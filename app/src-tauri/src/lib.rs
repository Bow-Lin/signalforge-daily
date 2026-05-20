use chrono::{DateTime, Datelike, Duration, Local, LocalResult, NaiveTime, TimeZone, Timelike, Utc};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    env,
    fs::{self, File, OpenOptions},
    io::{BufRead, BufReader, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration as StdDuration,
};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager, State,
};

#[derive(Default)]
struct AppState {
    active_run: Arc<Mutex<bool>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppConfig {
    workspace_path: String,
    output_path: String,
    ai_provider: AiProvider,
    digest_defaults: DigestDefaults,
    network: NetworkConfig,
    advanced: AdvancedConfig,
    #[serde(default = "default_sources")]
    sources: Vec<SourceConfig>,
    #[serde(default)]
    relevance_profile: RelevanceProfile,
    #[serde(default)]
    automation: AutomationConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AiProvider {
    provider: String,
    api_key: String,
    base_url: Option<String>,
    model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DigestDefaults {
    language: String,
    time_range_hours: u32,
    top_n: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct NetworkConfig {
    proxy_mode: String,
    http_proxy: Option<String>,
    https_proxy: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AdvancedConfig {
    feed_concurrency: Option<u32>,
    ai_retries: Option<u32>,
    max_ai_articles: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SourceConfig {
    id: String,
    name: String,
    #[serde(rename = "type")]
    source_type: String,
    url: String,
    enabled: bool,
    #[serde(default)]
    tags: Vec<String>,
    priority: String,
    created_at: String,
    updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RelevanceProfile {
    #[serde(default)]
    interested_topics: Vec<String>,
    #[serde(default)]
    muted_topics: Vec<String>,
    #[serde(default = "default_preferred_content_types")]
    preferred_content_types: Vec<String>,
    #[serde(default = "default_profile_language")]
    language: String,
}

impl Default for RelevanceProfile {
    fn default() -> Self {
        Self {
            interested_topics: Vec::new(),
            muted_topics: Vec::new(),
            preferred_content_types: default_preferred_content_types(),
            language: default_profile_language(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AutomationConfig {
    enabled: bool,
    frequency: String,
    time_of_day: String,
    notify_on_success: bool,
    notify_on_failure: bool,
    run_on_app_start_if_missed: bool,
    skip_if_already_generated_today: bool,
    paused_until: Option<String>,
}

impl Default for AutomationConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            frequency: "daily".to_string(),
            time_of_day: "08:30".to_string(),
            notify_on_success: true,
            notify_on_failure: true,
            run_on_app_start_if_missed: true,
            skip_if_already_generated_today: true,
            paused_until: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct AutomationState {
    last_scheduled_date: Option<String>,
    last_startup_missed_date: Option<String>,
    last_skip_at: Option<String>,
    last_skip_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppSnapshot {
    config: Option<AppConfig>,
    runs: Vec<RunRecord>,
    reports: Vec<ReportRecord>,
    source_stats: Vec<SourceRunStat>,
    feedback: Vec<ItemFeedback>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunRecord {
    id: String,
    #[serde(rename = "type")]
    run_type: String,
    status: String,
    #[serde(default = "default_run_trigger")]
    trigger: String,
    started_at: String,
    finished_at: Option<String>,
    duration_ms: Option<i64>,
    params_snapshot: ParamsSnapshot,
    stats: Option<RunStats>,
    output: Option<RunOutput>,
    top_picks: Option<Vec<TopPick>>,
    source_run_stats: Option<Vec<SourceRunStat>>,
    warnings: Option<RunWarnings>,
    error: Option<DigestError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ParamsSnapshot {
    language: String,
    time_range_hours: u32,
    top_n: u32,
    output_path: String,
    model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct RunStats {
    sources_scanned: Option<u32>,
    articles_fetched: Option<u32>,
    articles_selected: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunOutput {
    report_path: Option<String>,
    markdown_path: Option<String>,
    html_path: Option<String>,
    json_path: Option<String>,
    log_path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DigestError {
    #[serde(rename = "type")]
    error_type: String,
    message: String,
    raw: Option<String>,
    suggested_actions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunWarnings {
    feed_failures: Option<Vec<FeedFailure>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FeedFailure {
    source: String,
    reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TopPick {
    title: String,
    source: Option<String>,
    url: Option<String>,
    published_at: Option<String>,
    reason: Option<String>,
    item_id: Option<String>,
    matched_topics: Option<Vec<String>>,
    content_type: Option<String>,
    relevance_score: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SourceRunStat {
    run_id: String,
    source_id: String,
    source_name: String,
    source_type: String,
    enabled: bool,
    fetched_count: u32,
    candidate_count: u32,
    selected_count: u32,
    status: String,
    error_type: Option<String>,
    error_message: Option<String>,
    started_at: String,
    finished_at: String,
    duration_ms: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ItemFeedback {
    item_id: String,
    report_id: String,
    feedback: String,
    created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ReportRecord {
    id: String,
    run_id: String,
    title: String,
    generated_at: String,
    language: String,
    markdown_path: String,
    summary: Option<String>,
    top_picks: Option<Vec<TopPick>>,
    status: Option<String>,
    selected_count: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TestConnectionResult {
    ok: bool,
    message: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct AutomationStatus {
    enabled: bool,
    paused: bool,
    next_run_at: Option<String>,
    last_automation_run: Option<RunRecord>,
    last_skip_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "camelCase", rename_all_fields = "camelCase")]
enum DigestEvent {
    Started { run_id: String, record: RunRecord },
    Progress { run_id: String, step: String, message: String },
    Stats {
        run_id: String,
        sources_scanned: Option<u32>,
        articles_fetched: Option<u32>,
        articles_selected: Option<u32>,
    },
    Log { run_id: String, level: String, message: String },
    Completed { run_id: String, record: RunRecord },
    Failed { run_id: String, record: RunRecord },
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .manage(AppState::default())
        .setup(|app| {
            setup_tray(app)?;
            start_scheduler(app.handle().clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_snapshot,
            choose_folder,
            save_config,
            test_connection,
            generate_digest,
            get_automation_status,
            set_automation_paused,
            read_markdown,
            open_path,
            reveal_path,
            delete_run,
            save_item_feedback
        ])
        .run(tauri::generate_context!())
        .expect("error while running SignalForge Daily");
}

fn default_sources() -> Vec<SourceConfig> {
    Vec::new()
}

fn default_preferred_content_types() -> Vec<String> {
    vec![
        "engineering_blog".to_string(),
        "research_paper".to_string(),
        "open_source_release".to_string(),
        "product_update".to_string(),
        "opinion".to_string(),
    ]
}

fn default_profile_language() -> String {
    "mixed".to_string()
}

fn default_run_trigger() -> String {
    "manual".to_string()
}

fn built_in_sources() -> Vec<SourceConfig> {
    let now = Utc::now().to_rfc3339();
    let mut sources = Vec::new();
    let Ok(root) = repo_root() else {
        return sources;
    };
    let path = root.join("src").join("signalforge_daily").join("digest_feeds.py");
    let Ok(raw) = fs::read_to_string(path) else {
        return sources;
    };
    let Ok(regex) = Regex::new(r#"\("([^"]+)",\s*"([^"]+)""#) else {
        return sources;
    };
    for caps in regex.captures_iter(&raw) {
        let Some(name) = caps.get(1).map(|value| value.as_str().to_string()) else { continue };
        let Some(url) = caps.get(2).map(|value| value.as_str().to_string()) else { continue };
        let source_type = if url.contains("developers.openai.com") || url.contains("claude.com/blog") {
            "blog"
        } else {
            "rss"
        };
        sources.push(SourceConfig {
            id: stable_source_id(&url),
            name,
            source_type: source_type.to_string(),
            url,
            enabled: true,
            tags: Vec::new(),
            priority: "normal".to_string(),
            created_at: now.clone(),
            updated_at: now.clone(),
        });
    }
    sources
}

fn stable_source_id(value: &str) -> String {
    let mut hash: u64 = 1469598103934665603;
    for byte in value.as_bytes() {
        hash ^= *byte as u64;
        hash = hash.wrapping_mul(1099511628211);
    }
    format!("src-{hash:012x}")
}

#[tauri::command]
fn get_snapshot() -> Result<AppSnapshot, String> {
    snapshot()
}

#[tauri::command]
fn choose_folder() -> Result<Option<String>, String> {
    Ok(rfd::FileDialog::new()
        .set_title("Choose workspace folder")
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string()))
}

#[tauri::command]
fn save_config(config: AppConfig) -> Result<AppSnapshot, String> {
    persist_config(&config)?;
    snapshot()
}

#[tauri::command]
fn test_connection(config: AppConfig) -> Result<TestConnectionResult, String> {
    if config.ai_provider.api_key.trim().is_empty() {
        return Ok(TestConnectionResult {
            ok: false,
            message: "API key is not configured.".to_string(),
        });
    }
    if config.ai_provider.model.trim().is_empty() {
        return Ok(TestConnectionResult {
            ok: false,
            message: "Model is required.".to_string(),
        });
    }

    let script = r#"
import os
import sys

from openai import OpenAI

api_key = os.environ["IFLOW_API_KEY"]
base_url = os.environ.get("IFLOW_BASE_URL") or None
model = os.environ["IFLOW_MODEL"]

client = OpenAI(api_key=api_key, base_url=base_url)
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "ping"}],
    max_tokens=1,
    temperature=0,
)
choice_count = len(getattr(response, "choices", []) or [])
if choice_count < 1:
    raise RuntimeError("provider returned no choices")
print("ok")
"#;

    let root = repo_root()?;
    let mut command = python_command(&root);
    command
        .arg("-c")
        .arg(script)
        .current_dir(&root);
    apply_env(&mut command, &config);

    let output = command.output().map_err(|err| err.to_string())?;
    if output.status.success() {
        return Ok(TestConnectionResult {
            ok: true,
            message: "Connection test passed.".to_string(),
        });
    }

    let raw = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let error = classify_digest_error(&raw);
    Ok(TestConnectionResult {
        ok: false,
        message: format!("Connection test failed: {}", error.message),
    })
}

#[tauri::command]
fn generate_digest(app: AppHandle, state: State<AppState>) -> Result<RunRecord, String> {
    start_digest(app, state.active_run.clone(), "manual")
}

fn start_digest(app: AppHandle, active_run: Arc<Mutex<bool>>, trigger: &str) -> Result<RunRecord, String> {
    let config = load_config()?.ok_or_else(|| "Workspace is not configured".to_string())?;
    ensure_workspace_dirs(&config)?;
    if config.ai_provider.api_key.trim().is_empty() {
        let record = build_failed_preflight_run_record(&config, trigger, "API key is not configured");
        let run_id = record.id.clone();
        save_run(&config, &record)?;
        maybe_send_automation_notification(&app, &config, &record);
        emit(&app, DigestEvent::Failed { run_id, record: record.clone() });
        return Ok(record);
    }

    {
        let mut active = active_run
            .lock()
            .map_err(|_| "Unable to lock run state".to_string())?;
        if *active {
            return Err("Digest generation is already running".to_string());
        }
        *active = true;
    }

    let started = Utc::now();
    let (record, report_path, log_path) = build_running_run_record(&config, trigger, started);
    let run_id = record.id.clone();

    save_run(&config, &record)?;
    emit(&app, DigestEvent::Started { run_id: run_id.clone(), record: record.clone() });
    emit(
        &app,
        DigestEvent::Progress {
            run_id: run_id.clone(),
            step: "Preparing environment...".to_string(),
            message: "Preparing environment...".to_string(),
        },
    );

    let record_for_worker = record.clone();
    thread::spawn(move || {
        let _ = run_digest_process(app, config, record_for_worker, report_path, log_path);
        if let Ok(mut active) = active_run.lock() {
            *active = false;
        }
    });

    Ok(record)
}

fn build_running_run_record(config: &AppConfig, trigger: &str, started: DateTime<Utc>) -> (RunRecord, PathBuf, PathBuf) {
    let timestamp = started.format("%Y%m%d-%H%M%S").to_string();
    let run_id = format!("run-{}", timestamp);
    let report_path = Path::new(&config.output_path).join(format!("digest-{}.md", timestamp));
    let log_path = logs_dir(config).join(format!("{}.log", run_id));

    (
        RunRecord {
            id: run_id.clone(),
            run_type: "digest".to_string(),
            status: "running".to_string(),
            trigger: trigger.to_string(),
            started_at: started.to_rfc3339(),
            finished_at: None,
            duration_ms: None,
            params_snapshot: ParamsSnapshot {
                language: config.digest_defaults.language.clone(),
                time_range_hours: config.digest_defaults.time_range_hours,
                top_n: config.digest_defaults.top_n,
                output_path: config.output_path.clone(),
                model: config.ai_provider.model.clone(),
            },
            stats: None,
            output: Some(RunOutput {
                report_path: Some(report_path.to_string_lossy().to_string()),
                markdown_path: Some(report_path.to_string_lossy().to_string()),
                html_path: None,
                json_path: None,
                log_path: Some(log_path.to_string_lossy().to_string()),
            }),
            top_picks: None,
            source_run_stats: None,
            warnings: None,
            error: None,
        },
        report_path,
        log_path,
    )
}

fn build_failed_preflight_run_record(config: &AppConfig, trigger: &str, raw: &str) -> RunRecord {
    let started = Utc::now();
    let finished = Utc::now();
    let (mut record, _, _) = build_running_run_record(config, trigger, started);
    record.status = "failed".to_string();
    record.finished_at = Some(finished.to_rfc3339());
    record.duration_ms = Some(finished.signed_duration_since(started).num_milliseconds());
    record.error = Some(classify_digest_error(raw));
    record
}

#[tauri::command]
fn read_markdown(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|err| err.to_string())
}

#[tauri::command]
fn open_path(path: String) -> Result<(), String> {
    opener::open(path).map_err(|err| err.to_string())
}

#[tauri::command]
fn reveal_path(path: String) -> Result<(), String> {
    let path_ref = Path::new(&path);
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(format!("/select,{}", path_ref.to_string_lossy()))
            .spawn()
            .map_err(|err| err.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg("-R")
            .arg(path_ref)
            .spawn()
            .map_err(|err| err.to_string())?;
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let target = path_ref.parent().unwrap_or(path_ref);
        opener::open(target).map_err(|err| err.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn delete_run(run_id: String) -> Result<AppSnapshot, String> {
    if let Some(config) = load_config()? {
        let path = runs_dir(&config).join(format!("{}.json", run_id));
        if path.exists() {
            fs::remove_file(path).map_err(|err| err.to_string())?;
        }
    }
    snapshot()
}

#[tauri::command]
fn save_item_feedback(feedback: ItemFeedback) -> Result<AppSnapshot, String> {
    if let Some(config) = load_config()? {
        let mut items = read_feedback(&config)?;
        items.retain(|item| !(item.item_id == feedback.item_id && item.report_id == feedback.report_id));
        items.push(feedback);
        write_json(&feedback_path(&config), &items)?;
    }
    snapshot()
}

#[tauri::command]
fn get_automation_status() -> Result<AutomationStatus, String> {
    automation_status()
}

#[tauri::command]
fn set_automation_paused(paused: bool) -> Result<AppSnapshot, String> {
    let mut config = load_config()?.ok_or_else(|| "Workspace is not configured".to_string())?;
    config.automation.paused_until = if paused {
        Some((Utc::now() + Duration::days(3650)).to_rfc3339())
    } else {
        None
    };
    persist_config(&config)?;
    snapshot()
}

fn run_digest_process(
    app: AppHandle,
    config: AppConfig,
    mut record: RunRecord,
    report_path: PathBuf,
    log_path: PathBuf,
) -> Result<(), String> {
    let run_id = record.id.clone();
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .map_err(|err| err.to_string())?;

    let source_stats_output = metadata_dir(&config).join(format!("{}-source-stats.json", run_id));
    let mut command = digest_command(&config, &record.id, &report_path, &source_stats_output)?;
    command.stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = command.spawn().map_err(|err| err.to_string())?;
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    let raw_output = Arc::new(Mutex::new(String::new()));

    let stdout_handle = stdout.map(|stream| {
        read_process_stream(
            app.clone(),
            run_id.clone(),
            stream,
            "info",
            log_file.try_clone().ok(),
            raw_output.clone(),
        )
    });
    let stderr_handle = stderr.map(|stream| {
        read_process_stream(
            app.clone(),
            run_id.clone(),
            stream,
            "error",
            log_file.try_clone().ok(),
            raw_output.clone(),
        )
    });

    let status = child.wait().map_err(|err| err.to_string())?;
    if let Some(handle) = stdout_handle {
        let _ = handle.join();
    }
    if let Some(handle) = stderr_handle {
        let _ = handle.join();
    }

    let raw = raw_output.lock().map(|value| value.clone()).unwrap_or_default();
    let finished = Utc::now();
    record.finished_at = Some(finished.to_rfc3339());
    record.duration_ms = Some(
        DateTime::parse_from_rfc3339(&record.started_at)
            .map(|started| finished.signed_duration_since(started.with_timezone(&Utc)).num_milliseconds())
            .unwrap_or_default(),
    );

    if (status.success() || is_post_report_output_error(&raw)) && report_path.exists() {
        let markdown = fs::read_to_string(&report_path).unwrap_or_default();
        let source_run_stats = read_source_stats_output(&source_stats_output).unwrap_or_default();
        record.status = "success".to_string();
        record.top_picks = Some(parse_top_picks(&markdown));
        record.source_run_stats = Some(source_run_stats.clone());
        record.stats = parse_stats(&raw);
        let _ = save_source_stats(&config, &source_run_stats);
        let feed_failures = parse_feed_failures(&raw);
        if !feed_failures.is_empty() {
            record.warnings = Some(RunWarnings {
                feed_failures: Some(feed_failures),
            });
        }
        save_run(&config, &record)?;
        emit(
            &app,
            DigestEvent::Progress {
                run_id: run_id.clone(),
                step: "Completed".to_string(),
                message: "Digest generated successfully.".to_string(),
            },
        );
        maybe_send_automation_notification(&app, &config, &record);
        emit(&app, DigestEvent::Completed { run_id, record });
    } else {
        let error = classify_digest_error(&raw);
        let source_run_stats = read_source_stats_output(&source_stats_output).unwrap_or_default();
        record.status = "failed".to_string();
        record.source_run_stats = Some(source_run_stats.clone());
        record.error = Some(error);
        let _ = save_source_stats(&config, &source_run_stats);
        save_run(&config, &record)?;
        maybe_send_automation_notification(&app, &config, &record);
        emit(&app, DigestEvent::Failed { run_id, record });
    }

    let _ = log_file.flush();
    Ok(())
}

fn read_process_stream<R: std::io::Read + Send + 'static>(
    app: AppHandle,
    run_id: String,
    stream: R,
    level: &str,
    mut log_file: Option<File>,
    raw_output: Arc<Mutex<String>>,
) -> thread::JoinHandle<()> {
    let level = level.to_string();
    thread::spawn(move || {
        let reader = BufReader::new(stream);
        for line in reader.lines().map_while(Result::ok) {
            if let Some(file) = log_file.as_mut() {
                let _ = writeln!(file, "{}", line);
            }
            if let Ok(mut raw) = raw_output.lock() {
                raw.push_str(&line);
                raw.push('\n');
            }
            emit(
                &app,
                DigestEvent::Log {
                    run_id: run_id.clone(),
                    level: level.clone(),
                    message: line.clone(),
                },
            );
            if let Some(step) = progress_from_line(&line) {
                emit(
                    &app,
                    DigestEvent::Progress {
                        run_id: run_id.clone(),
                        step,
                        message: line.clone(),
                    },
                );
            }
            if let Some(stats) = parse_stats(&line) {
                emit(
                    &app,
                    DigestEvent::Stats {
                        run_id: run_id.clone(),
                        sources_scanned: stats.sources_scanned,
                        articles_fetched: stats.articles_fetched,
                        articles_selected: stats.articles_selected,
                    },
                );
            }
        }
    })
}

fn maybe_send_automation_notification(app: &AppHandle, config: &AppConfig, record: &RunRecord) {
    if record.trigger == "manual" {
        return;
    }
    let should_notify = (record.status == "success" && config.automation.notify_on_success)
        || (record.status == "failed" && config.automation.notify_on_failure);
    if !should_notify {
        return;
    }
    let (title, body) = if record.status == "success" {
        let sources = record
            .stats
            .as_ref()
            .and_then(|stats| stats.sources_scanned)
            .unwrap_or(0);
        let selected = record
            .stats
            .as_ref()
            .and_then(|stats| stats.articles_selected)
            .unwrap_or(0);
        (
            "今日摘要已生成",
            format!("已从 {sources} 个信息源中筛选出 {selected} 条重要更新。"),
        )
    } else {
        (
            "今日摘要生成失败",
            "点击查看失败原因和修复建议。".to_string(),
        )
    };
    let _ = app.emit("app:navigate", "today");
    let _ = app.emit("automation:notify", serde_json::json!({ "title": title, "body": body }));
}

fn read_source_stats_output(path: &Path) -> Result<Vec<SourceRunStat>, String> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    read_json(path)
}

fn digest_command(
    config: &AppConfig,
    run_id: &str,
    report_path: &Path,
    source_stats_output: &Path,
) -> Result<Command, String> {
    let sources_path = metadata_dir(config).join(format!("{}-sources.json", run_id));
    let profile_path = metadata_dir(config).join(format!("{}-relevance-profile.json", run_id));
    write_json(&sources_path, &config.sources)?;
    write_json(&profile_path, &config.relevance_profile)?;
    let mut args = vec![
        "--hours".to_string(),
        config.digest_defaults.time_range_hours.to_string(),
        "--top-n".to_string(),
        config.digest_defaults.top_n.to_string(),
        "--lang".to_string(),
        config.digest_defaults.language.clone(),
        "--output".to_string(),
        report_path.to_string_lossy().to_string(),
        "--iflow-key".to_string(),
        config.ai_provider.api_key.clone(),
        "--iflow-model".to_string(),
        config.ai_provider.model.clone(),
        "--feed-concurrency".to_string(),
        config.advanced.feed_concurrency.unwrap_or(10).to_string(),
        "--ai-retries".to_string(),
        config.advanced.ai_retries.unwrap_or(1).to_string(),
        "--max-ai-articles".to_string(),
        config.advanced.max_ai_articles.unwrap_or(120).to_string(),
        "--sources-config".to_string(),
        sources_path.to_string_lossy().to_string(),
        "--relevance-profile".to_string(),
        profile_path.to_string_lossy().to_string(),
        "--source-stats-output".to_string(),
        source_stats_output.to_string_lossy().to_string(),
        "--run-id".to_string(),
        run_id.to_string(),
    ];
    if let Some(base_url) = config.ai_provider.base_url.as_ref().filter(|value| !value.trim().is_empty()) {
        args.push("--iflow-base-url".to_string());
        args.push(base_url.clone());
    }

    let sidecar = env::var("SIGNALFORGE_DAILY_DIGEST_SIDECAR")
        .or_else(|_| env::var("NEWS_COLLECTION_DIGEST_SIDECAR"))
        .ok()
        .filter(|value| !value.trim().is_empty());
    let mut command = if let Some(path) = sidecar {
        let mut cmd = Command::new(path);
        cmd.args(args);
        cmd
    } else {
        let root = repo_root()?;
        let mut cmd = python_command(&root);
        cmd.arg("-m")
            .arg("signalforge_daily.digest_cli")
            .args(args);
        cmd
    };

    command.current_dir(repo_root()?);
    apply_env(&mut command, config);
    Ok(command)
}

fn apply_env(command: &mut Command, config: &AppConfig) {
    command.env("PYTHONIOENCODING", "utf-8");
    command.env("PYTHONUTF8", "1");
    command.env("IFLOW_API_KEY", &config.ai_provider.api_key);
    if let Some(base_url) = config.ai_provider.base_url.as_ref().filter(|value| !value.trim().is_empty()) {
        command.env("IFLOW_BASE_URL", base_url);
    }
    command.env("IFLOW_MODEL", &config.ai_provider.model);

    match config.network.proxy_mode.as_str() {
        "none" => {
            for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"] {
                command.env_remove(key);
            }
        }
        "custom" => {
            if let Some(value) = config.network.http_proxy.as_ref().filter(|value| !value.trim().is_empty()) {
                command.env("HTTP_PROXY", value);
            }
            if let Some(value) = config.network.https_proxy.as_ref().filter(|value| !value.trim().is_empty()) {
                command.env("HTTPS_PROXY", value);
            }
        }
        _ => {}
    }
}

fn python_command(repo_root: &Path) -> Command {
    let windows_python = repo_root.join(".venv").join("Scripts").join("python.exe");
    let unix_python = repo_root.join(".venv").join("bin").join("python");
    let mut command = if windows_python.exists() {
        Command::new(windows_python)
    } else if unix_python.exists() {
        Command::new(unix_python)
    } else {
        let mut fallback = Command::new("uv");
        fallback.arg("run").arg("--no-project").arg("python");
        fallback
    };

    let src_path = repo_root.join("src").to_string_lossy().to_string();
    let separator = if cfg!(windows) { ";" } else { ":" };
    let python_path = match env::var("PYTHONPATH") {
        Ok(existing) if !existing.trim().is_empty() => format!("{src_path}{separator}{existing}"),
        _ => src_path,
    };
    command.env("PYTHONPATH", python_path);
    command
}

fn snapshot() -> Result<AppSnapshot, String> {
    let config = load_config()?;
    let runs = config.as_ref().map(read_runs).transpose()?.unwrap_or_default();
    let reports = config
        .as_ref()
        .map(|cfg| read_reports(cfg, &runs))
        .transpose()?
        .unwrap_or_default();
    let source_stats = config
        .as_ref()
        .map(read_source_stats)
        .transpose()?
        .unwrap_or_default();
    let feedback = config
        .as_ref()
        .map(read_feedback)
        .transpose()?
        .unwrap_or_default();
    Ok(AppSnapshot { config, runs, reports, source_stats, feedback })
}

fn load_config() -> Result<Option<AppConfig>, String> {
    let pointer_path = pointer_config_path()?;
    if pointer_path.exists() {
        let pointer: serde_json::Value = read_json(&pointer_path)?;
        if let Some(workspace) = pointer.get("workspacePath").and_then(|value| value.as_str()) {
            let workspace_config = Path::new(workspace).join("app-config.json");
            if workspace_config.exists() {
                let mut config: AppConfig = read_json(&workspace_config)?;
                hydrate_config_defaults(&mut config);
                return Ok(Some(config));
            }
        }
    }
    Ok(None)
}

fn hydrate_config_defaults(config: &mut AppConfig) {
    if config.sources.is_empty() {
        config.sources = built_in_sources();
    }
    if config.relevance_profile.preferred_content_types.is_empty() {
        config.relevance_profile.preferred_content_types = default_preferred_content_types();
    }
    if config.relevance_profile.language.trim().is_empty() {
        config.relevance_profile.language = default_profile_language();
    }
    if config.automation.frequency.trim().is_empty() {
        config.automation.frequency = "daily".to_string();
    }
    if NaiveTime::parse_from_str(&config.automation.time_of_day, "%H:%M").is_err() {
        config.automation.time_of_day = "08:30".to_string();
    }
}

fn persist_config(config: &AppConfig) -> Result<(), String> {
    let mut config = config.clone();
    hydrate_config_defaults(&mut config);
    ensure_workspace_dirs(&config)?;
    write_json(&Path::new(&config.workspace_path).join("app-config.json"), &config)?;
    let pointer_path = pointer_config_path()?;
    if let Some(parent) = pointer_path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let mut pointer = HashMap::new();
    pointer.insert("workspacePath", config.workspace_path.clone());
    write_json(&pointer_path, &pointer)
}

fn ensure_workspace_dirs(config: &AppConfig) -> Result<(), String> {
    fs::create_dir_all(&config.workspace_path).map_err(|err| err.to_string())?;
    fs::create_dir_all(&config.output_path).map_err(|err| err.to_string())?;
    fs::create_dir_all(runs_dir(config)).map_err(|err| err.to_string())?;
    fs::create_dir_all(logs_dir(config)).map_err(|err| err.to_string())?;
    fs::create_dir_all(metadata_dir(config)).map_err(|err| err.to_string())
}

fn read_runs(config: &AppConfig) -> Result<Vec<RunRecord>, String> {
    let dir = runs_dir(config);
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut runs = Vec::new();
    for entry in fs::read_dir(dir).map_err(|err| err.to_string())? {
        let path = entry.map_err(|err| err.to_string())?.path();
        if path.extension().and_then(|value| value.to_str()) == Some("json") {
            if let Ok(mut run) = read_json::<RunRecord>(&path) {
                if run.status == "running" {
                    run.status = "failed".to_string();
                    run.error = Some(DigestError {
                        error_type: "unknown".to_string(),
                        message: "Digest was interrupted. The application may have been closed while generation was in progress.".to_string(),
                        raw: None,
                        suggested_actions: vec!["Retry the digest generation".to_string()],
                    });
                    let _ = write_json(&path, &run);
                }
                if normalize_finished_report_run(&mut run) {
                    let _ = write_json(&path, &run);
                }
                runs.push(run);
            }
        }
    }
    runs.sort_by(|a, b| b.started_at.cmp(&a.started_at));
    Ok(runs)
}

fn read_reports(config: &AppConfig, runs: &[RunRecord]) -> Result<Vec<ReportRecord>, String> {
    let mut reports: HashMap<String, ReportRecord> = HashMap::new();
    for run in runs {
        let Some(output) = run.output.as_ref() else { continue };
        let Some(markdown_path) = output.markdown_path.as_ref().or(output.report_path.as_ref()) else {
            continue;
        };
        let path = Path::new(markdown_path);
        if run.status != "success" || !path.exists() {
            continue;
        }
        let markdown = fs::read_to_string(path).unwrap_or_default();
        reports.insert(
            markdown_path.clone(),
            ReportRecord {
                id: format!("report-{}", run.id),
                run_id: run.id.clone(),
                title: report_title(&markdown, path),
                generated_at: run.finished_at.clone().unwrap_or_else(|| run.started_at.clone()),
                language: run.params_snapshot.language.clone(),
                markdown_path: markdown_path.clone(),
                summary: Some(markdown.chars().take(240).collect()),
                top_picks: run.top_picks.clone().or_else(|| Some(parse_top_picks(&markdown))),
                status: Some("success".to_string()),
                selected_count: run.stats.as_ref().and_then(|stats| stats.articles_selected),
            },
        );
    }

    let output_dir = Path::new(&config.output_path);
    if output_dir.exists() {
        for entry in fs::read_dir(output_dir).map_err(|err| err.to_string())? {
            let path = entry.map_err(|err| err.to_string())?.path();
            if path.extension().and_then(|value| value.to_str()) != Some("md") {
                continue;
            }
            let markdown_path = path.to_string_lossy().to_string();
            if reports.contains_key(&markdown_path) {
                continue;
            }
            let markdown = fs::read_to_string(&path).unwrap_or_default();
            let generated_at = fs::metadata(&path)
                .and_then(|meta| meta.modified())
                .map(DateTime::<Local>::from)
                .map(|value| value.to_rfc3339())
                .unwrap_or_else(|_| Utc::now().to_rfc3339());
            reports.insert(
                markdown_path.clone(),
                ReportRecord {
                    id: format!("file-{}", sanitize_id(&markdown_path)),
                    run_id: String::new(),
                    title: report_title(&markdown, &path),
                    generated_at,
                    language: config.digest_defaults.language.clone(),
                    markdown_path,
                    summary: Some(markdown.chars().take(240).collect()),
                    top_picks: Some(parse_top_picks(&markdown)),
                    status: Some("success".to_string()),
                    selected_count: None,
                },
            );
        }
    }

    let mut list: Vec<ReportRecord> = reports.into_values().collect();
    list.sort_by(|a, b| b.generated_at.cmp(&a.generated_at));
    Ok(list)
}

fn save_run(config: &AppConfig, record: &RunRecord) -> Result<(), String> {
    write_json(&runs_dir(config).join(format!("{}.json", record.id)), record)
}

fn setup_tray(app: &mut tauri::App) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "tray_open", "打开 SignalForge Daily", true, None::<&str>)?;
    let generate = MenuItem::with_id(app, "tray_generate", "生成今日摘要", true, None::<&str>)?;
    let latest_report = MenuItem::with_id(app, "tray_report", "打开最新报告", true, None::<&str>)?;
    let sources = MenuItem::with_id(app, "tray_sources", "查看信息源状态", true, None::<&str>)?;
    let pause = MenuItem::with_id(app, "tray_pause", "暂停自动生成 / 恢复自动生成", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "tray_quit", "退出", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let menu = Menu::with_items(app, &[&open, &generate, &latest_report, &sources, &pause, &separator, &quit])?;
    let mut tray = TrayIconBuilder::with_id("main")
        .menu(&menu)
        .tooltip("SignalForge Daily")
        .show_menu_on_left_click(true)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "tray_open" => {
                show_main_window(app);
                let _ = app.emit("app:navigate", "today");
            }
            "tray_generate" => {
                show_main_window(app);
                let active_run = app.state::<AppState>().active_run.clone();
                if let Err(err) = start_digest(app.clone(), active_run, "manual") {
                    let _ = app.emit("digest:event", DigestEvent::Log {
                        run_id: "tray".to_string(),
                        level: "warn".to_string(),
                        message: err,
                    });
                }
            }
            "tray_report" => {
                show_main_window(app);
                let _ = app.emit("app:navigate", "reports");
            }
            "tray_sources" => {
                show_main_window(app);
                let _ = app.emit("app:navigate", "sources");
            }
            "tray_pause" => {
                if let Ok(Some(mut config)) = load_config() {
                    config.automation.paused_until = if is_automation_paused(&config.automation) {
                        None
                    } else {
                        Some((Utc::now() + Duration::days(3650)).to_rfc3339())
                    };
                    let _ = persist_config(&config);
                    let _ = app.emit("automation:changed", ());
                }
            }
            "tray_quit" => app.exit(0),
            _ => {}
        });
    if let Some(icon) = app.default_window_icon().cloned() {
        tray = tray.icon(icon);
    }
    tray.build(app)?;
    Ok(())
}

fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn start_scheduler(app: AppHandle) {
    let active_run = app.state::<AppState>().active_run.clone();
    thread::spawn(move || {
        let mut first_tick = true;
        loop {
            if let Ok(Some(config)) = load_config() {
                let _ = scheduler_tick(&app, active_run.clone(), &config, first_tick);
            }
            first_tick = false;
            thread::sleep(StdDuration::from_secs(30));
        }
    });
}

fn scheduler_tick(app: &AppHandle, active_run: Arc<Mutex<bool>>, config: &AppConfig, first_tick: bool) -> Result<(), String> {
    if !config.automation.enabled || is_automation_paused(&config.automation) {
        return Ok(());
    }
    let now = Local::now();
    if !is_frequency_day(&config.automation, now) {
        return Ok(());
    }
    let Some(due_at) = scheduled_local_for_date(&config.automation, now) else {
        return Ok(());
    };
    if now < due_at {
        return Ok(());
    }

    let today = now.format("%Y-%m-%d").to_string();
    let mut state = read_automation_state(config).unwrap_or_default();
    if first_tick && config.automation.run_on_app_start_if_missed && state.last_startup_missed_date.as_deref() != Some(&today) {
        if config.automation.skip_if_already_generated_today && has_successful_digest_today(config)? {
            mark_startup_missed_consumed(&mut state, &today, Some("今天已生成摘要，启动补跑已跳过。".to_string()));
            return write_automation_state(config, &state);
        }
        if *active_run.lock().map_err(|_| "Unable to lock run state".to_string())? {
            mark_startup_missed_consumed(&mut state, &today, Some("已有摘要任务正在运行，启动补跑已跳过。".to_string()));
            return write_automation_state(config, &state);
        }
        mark_startup_missed_consumed(&mut state, &today, None);
        write_automation_state(config, &state)?;
        return start_digest(app.clone(), active_run, "startup_missed").map(|_| ());
    }

    if state.last_scheduled_date.as_deref() == Some(&today) {
        return Ok(());
    }
    if config.automation.skip_if_already_generated_today && has_successful_digest_today(config)? {
        state.last_scheduled_date = Some(today);
        state.last_skip_at = Some(Utc::now().to_rfc3339());
        state.last_skip_reason = Some("今天已生成摘要，计划任务已跳过。".to_string());
        return write_automation_state(config, &state);
    }
    if *active_run.lock().map_err(|_| "Unable to lock run state".to_string())? {
        state.last_scheduled_date = Some(today);
        state.last_skip_at = Some(Utc::now().to_rfc3339());
        state.last_skip_reason = Some("已有摘要任务正在运行，计划任务已跳过。".to_string());
        return write_automation_state(config, &state);
    }
    state.last_scheduled_date = Some(today);
    write_automation_state(config, &state)?;
    start_digest(app.clone(), active_run, "scheduled").map(|_| ())
}

fn mark_startup_missed_consumed(state: &mut AutomationState, today: &str, skip_reason: Option<String>) {
    state.last_startup_missed_date = Some(today.to_string());
    state.last_scheduled_date = Some(today.to_string());
    match skip_reason {
        Some(reason) => {
            state.last_skip_at = Some(Utc::now().to_rfc3339());
            state.last_skip_reason = Some(reason);
        }
        None => {
            state.last_skip_at = None;
            state.last_skip_reason = None;
        }
    }
}

fn automation_status() -> Result<AutomationStatus, String> {
    let Some(config) = load_config()? else {
        return Ok(AutomationStatus {
            enabled: false,
            paused: false,
            next_run_at: None,
            last_automation_run: None,
            last_skip_reason: None,
        });
    };
    let runs = read_runs(&config)?;
    let last_automation_run = runs
        .iter()
        .find(|run| run.trigger == "scheduled" || run.trigger == "startup_missed")
        .cloned();
    let state = read_automation_state(&config).unwrap_or_default();
    Ok(AutomationStatus {
        enabled: config.automation.enabled,
        paused: is_automation_paused(&config.automation),
        next_run_at: next_run_at(&config.automation).map(|value| value.to_rfc3339()),
        last_automation_run,
        last_skip_reason: state.last_skip_reason,
    })
}

fn next_run_at(automation: &AutomationConfig) -> Option<DateTime<Local>> {
    if !automation.enabled || is_automation_paused(automation) {
        return None;
    }
    let now = Local::now();
    for offset in 0..14 {
        let candidate_date = now.date_naive() + Duration::days(offset);
        let midnight = match Local.with_ymd_and_hms(candidate_date.year(), candidate_date.month(), candidate_date.day(), 0, 0, 0) {
            LocalResult::Single(value) => value,
            LocalResult::Ambiguous(value, _) => value,
            LocalResult::None => continue,
        };
        if !is_frequency_day(automation, midnight) {
            continue;
        }
        let candidate = scheduled_local_for_date(automation, midnight)?;
        if candidate > now {
            return Some(candidate);
        }
    }
    None
}

fn scheduled_local_for_date(automation: &AutomationConfig, date: DateTime<Local>) -> Option<DateTime<Local>> {
    let time = NaiveTime::parse_from_str(&automation.time_of_day, "%H:%M")
        .unwrap_or_else(|_| NaiveTime::from_hms_opt(8, 30, 0).expect("valid default automation time"));
    match Local.with_ymd_and_hms(date.year(), date.month(), date.day(), time.hour(), time.minute(), 0) {
        LocalResult::Single(value) => Some(value),
        LocalResult::Ambiguous(value, _) => Some(value),
        LocalResult::None => None,
    }
}

fn is_frequency_day(automation: &AutomationConfig, date: DateTime<Local>) -> bool {
    automation.frequency != "weekdays" || date.weekday().number_from_monday() <= 5
}

fn is_automation_paused(automation: &AutomationConfig) -> bool {
    automation
        .paused_until
        .as_deref()
        .and_then(|value| DateTime::parse_from_rfc3339(value).ok())
        .map(|value| value.with_timezone(&Utc) > Utc::now())
        .unwrap_or(false)
}

fn has_successful_digest_today(config: &AppConfig) -> Result<bool, String> {
    Ok(read_runs(config)?.iter().any(|run| {
        run.status == "success"
            && DateTime::parse_from_rfc3339(run.finished_at.as_deref().unwrap_or(&run.started_at))
                .map(|value| value.with_timezone(&Local).date_naive() == Local::now().date_naive())
                .unwrap_or(false)
    }))
}

fn read_source_stats(config: &AppConfig) -> Result<Vec<SourceRunStat>, String> {
    let path = source_stats_path(config);
    if !path.exists() {
        return Ok(Vec::new());
    }
    read_json(&path)
}

fn save_source_stats(config: &AppConfig, stats: &[SourceRunStat]) -> Result<(), String> {
    let mut existing = read_source_stats(config)?;
    existing.extend_from_slice(stats);
    existing.sort_by(|a, b| b.started_at.cmp(&a.started_at));
    write_json(&source_stats_path(config), &existing)
}

fn read_feedback(config: &AppConfig) -> Result<Vec<ItemFeedback>, String> {
    let path = feedback_path(config);
    if !path.exists() {
        return Ok(Vec::new());
    }
    read_json(&path)
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, String> {
    let raw = fs::read_to_string(path).map_err(|err| err.to_string())?;
    serde_json::from_str(&raw).map_err(|err| err.to_string())
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let raw = serde_json::to_string_pretty(value).map_err(|err| err.to_string())?;
    fs::write(path, raw).map_err(|err| err.to_string())
}

fn pointer_config_path() -> Result<PathBuf, String> {
    let dir = dirs::config_dir()
        .ok_or_else(|| "Unable to resolve local config directory".to_string())?
        .join("signalforge-daily");
    Ok(dir.join("workspace-pointer.json"))
}

fn runs_dir(config: &AppConfig) -> PathBuf {
    Path::new(&config.workspace_path).join("runs")
}

fn logs_dir(config: &AppConfig) -> PathBuf {
    Path::new(&config.workspace_path).join("logs")
}

fn metadata_dir(config: &AppConfig) -> PathBuf {
    Path::new(&config.workspace_path).join("metadata")
}

fn source_stats_path(config: &AppConfig) -> PathBuf {
    metadata_dir(config).join("source-run-stats.json")
}

fn feedback_path(config: &AppConfig) -> PathBuf {
    metadata_dir(config).join("item-feedback.json")
}

fn automation_state_path(config: &AppConfig) -> PathBuf {
    metadata_dir(config).join("automation-state.json")
}

fn read_automation_state(config: &AppConfig) -> Result<AutomationState, String> {
    let path = automation_state_path(config);
    if !path.exists() {
        return Ok(AutomationState::default());
    }
    read_json(&path)
}

fn write_automation_state(config: &AppConfig, state: &AutomationState) -> Result<(), String> {
    write_json(&automation_state_path(config), state)
}

fn repo_root() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .ok_or_else(|| "Unable to resolve repository root".to_string())
}

fn emit(app: &AppHandle, event: DigestEvent) {
    let _ = app.emit("digest:event", event);
}

fn progress_from_line(line: &str) -> Option<String> {
    let lower = line.to_lowercase();
    if lower.contains("fetching") {
        Some("Fetching feeds...".to_string())
    } else if lower.contains("filtering") {
        Some("Filtering articles...".to_string())
    } else if lower.contains("scoring") {
        Some("Scoring articles...".to_string())
    } else if lower.contains("generating summaries") || lower.contains("generating highlights") {
        Some("Generating summaries...".to_string())
    } else if lower.contains("report:") || lower.contains("done") {
        Some("Writing report...".to_string())
    } else {
        None
    }
}

fn parse_stats(raw: &str) -> Option<RunStats> {
    if let Some(caps) = Regex::new(r"Stats:\s*(\d+)\s+sources\s+(?:→|->)\s+(\d+)\s+articles\s+(?:→|->)\s+(\d+)\s+recent\s+(?:→|->)\s+(\d+)\s+selected")
        .ok()?
        .captures(raw)
    {
        return Some(RunStats {
            sources_scanned: caps.get(1).and_then(|value| value.as_str().parse().ok()),
            articles_fetched: caps.get(2).and_then(|value| value.as_str().parse().ok()),
            articles_selected: caps.get(4).and_then(|value| value.as_str().parse().ok()),
        });
    }

    let progress_regex = Regex::new(r"Progress:\s*(\d+)/(\d+)\s+feeds processed\s+\((\d+)\s+ok,\s+(\d+)\s+failed\)").ok()?;
    let last_progress = progress_regex.captures_iter(raw).last();
    let Some(caps) = last_progress else {
        return None;
    };
    let selected = Regex::new(r"Generating summaries:\s*(\d+)\s+articles")
        .ok()
        .and_then(|regex| regex.captures(raw))
        .and_then(|caps| caps.get(1).and_then(|value| value.as_str().parse().ok()));
    Some(RunStats {
        sources_scanned: caps.get(2).and_then(|value| value.as_str().parse().ok()),
        articles_fetched: None,
        articles_selected: selected,
    })
}

fn parse_feed_failures(raw: &str) -> Vec<FeedFailure> {
    let Ok(regex) = Regex::new(r"(?m)^\[digest\]\s*(?:⚠️\s*)?Feed failure:\s*(?P<source>.+?)\s*\|\s*(?P<reason>.+?)\s*$") else {
        return Vec::new();
    };
    let mut failures: Vec<FeedFailure> = regex
        .captures_iter(raw)
        .map(|caps| FeedFailure {
            source: caps
                .name("source")
                .map(|value| value.as_str().trim().to_string())
                .unwrap_or_default(),
            reason: caps
                .name("reason")
                .map(|value| value.as_str().trim().to_string())
                .unwrap_or_default(),
        })
        .filter(|failure| !failure.source.is_empty())
        .collect();

    if !failures.is_empty() {
        return failures;
    }

    let Ok(warning_regex) = Regex::new(r"(?m)\[digest\]\s*(?:✗|\\u2717)\s*(?P<source>[^:]+):\s*(?P<reason>.+?)\s*$") else {
        return Vec::new();
    };
    failures = warning_regex
        .captures_iter(raw)
        .map(|caps| FeedFailure {
            source: caps
                .name("source")
                .map(|value| value.as_str().trim().to_string())
                .unwrap_or_default(),
            reason: caps
                .name("reason")
                .map(|value| value.as_str().trim().to_string())
                .unwrap_or_default(),
        })
        .filter(|failure| !failure.source.is_empty())
        .collect();

    if !failures.is_empty() {
        return failures;
    }

    parse_feed_progress(raw)
        .and_then(|(_, _, ok, failed)| {
            (failed > 0).then(|| FeedFailure {
                source: format!("{failed} failed feeds"),
                reason: format!("{ok} feeds succeeded. Open the run log for source-level details."),
            })
        })
        .into_iter()
        .collect()
}

fn parse_feed_progress(raw: &str) -> Option<(u32, u32, u32, u32)> {
    let regex = Regex::new(r"Progress:\s*(\d+)/(\d+)\s+feeds processed\s+\((\d+)\s+ok,\s+(\d+)\s+failed\)").ok()?;
    let caps = regex.captures_iter(raw).last()?;
    Some((
        caps.get(1)?.as_str().parse().ok()?,
        caps.get(2)?.as_str().parse().ok()?,
        caps.get(3)?.as_str().parse().ok()?,
        caps.get(4)?.as_str().parse().ok()?,
    ))
}

fn is_post_report_output_error(raw: &str) -> bool {
    let lower = raw.to_lowercase();
    lower.contains("unicodeencodeerror") && (lower.contains("[digest] done") || lower.contains("step 5/5"))
}

fn normalize_finished_report_run(run: &mut RunRecord) -> bool {
    if run.status != "failed" {
        return false;
    }
    let Some(output) = run.output.as_ref() else {
        return false;
    };
    let Some(markdown_path) = output.markdown_path.as_ref().or(output.report_path.as_ref()) else {
        return false;
    };
    if !Path::new(markdown_path).exists() {
        return false;
    }
    let raw = run
        .error
        .as_ref()
        .and_then(|error| error.raw.as_deref())
        .unwrap_or_default()
        .to_string();
    let error_type = run
        .error
        .as_ref()
        .map(|error| error.error_type.as_str())
        .unwrap_or_default();
    if error_type != "feed_fetch_failed" && !is_post_report_output_error(&raw) {
        return false;
    }

    let markdown = fs::read_to_string(markdown_path).unwrap_or_default();
    let feed_failures = parse_feed_failures(&raw);
    run.status = "success".to_string();
    run.error = None;
    run.stats = parse_stats(&raw).or_else(|| run.stats.clone());
    run.top_picks = Some(parse_top_picks(&markdown));
    if !feed_failures.is_empty() {
        run.warnings = Some(RunWarnings {
            feed_failures: Some(feed_failures),
        });
    }
    true
}

fn parse_top_picks(markdown: &str) -> Vec<TopPick> {
    let section = markdown
        .split("## 🏆 今日必读")
        .nth(1)
        .and_then(|value| value.split("---").next())
        .unwrap_or("");
    let Ok(regex) = Regex::new(r"(?s)(?:🥇|🥈|🥉)\s+\*\*(?P<title>.+?)\*\*.*?\[(?P<original>.+?)\]\((?P<url>.+?)\)\s+—\s+(?P<source>.+?)\s+·.*?(?:💡 \*\*(?:为什么值得读|Why selected)\*\*: (?P<reason>.+?)\n)?") else {
        return Vec::new();
    };
    regex
        .captures_iter(section)
        .take(3)
        .map(|caps| TopPick {
            title: caps
                .name("title")
                .or_else(|| caps.name("original"))
                .map(|value| value.as_str().trim().to_string())
                .unwrap_or_default(),
            source: caps.name("source").map(|value| value.as_str().trim().to_string()),
            url: caps.name("url").map(|value| value.as_str().trim().to_string()),
            published_at: None,
            reason: caps.name("reason").map(|value| value.as_str().trim().to_string()),
            item_id: None,
            matched_topics: None,
            content_type: None,
            relevance_score: None,
        })
        .collect()
}

fn report_title(markdown: &str, path: &Path) -> String {
    markdown
        .lines()
        .find_map(|line| line.strip_prefix("# ").map(str::trim))
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .unwrap_or_else(|| {
            path.file_name()
                .and_then(|value| value.to_str())
                .unwrap_or("Digest Report")
                .to_string()
        })
}

fn sanitize_id(value: &str) -> String {
    value
        .chars()
        .map(|ch| if ch.is_ascii_alphanumeric() { ch } else { '-' })
        .collect()
}

fn classify_digest_error(raw: &str) -> DigestError {
    let lower = raw.to_lowercase();
    if lower.contains("api key") || lower.contains("iflow_api_key") || lower.contains("missing") {
        return digest_error(
            "missing_api_key",
            "API key is not configured.",
            raw,
            &["Go to Settings and configure API key", "Test connection before generating digest"],
        );
    }
    if lower.contains("127.0.0.1:7890") || lower.contains("proxy") || lower.contains("tunnel") {
        return digest_error(
            "proxy_error",
            "Network proxy may be unavailable.",
            raw,
            &["Check whether your proxy is running", "Switch proxy mode to No proxy", "Update custom proxy address"],
        );
    }
    if lower.contains("no articles fetched") || lower.contains("no articles found") {
        return digest_error(
            "no_articles_fetched",
            "No articles were fetched from configured sources.",
            raw,
            &["Check internet connection", "Increase time range", "Retry later"],
        );
    }
    if lower.contains("feed") && (lower.contains("failed") || lower.contains("timeout")) {
        return digest_error(
            "feed_fetch_failed",
            "One or more feeds failed to load.",
            raw,
            &["Check internet connection", "Try again later", "Review the run log"],
        );
    }
    if lower.contains("chat.completions") || lower.contains("model") || lower.contains("ai response") {
        return digest_error(
            "model_generation_failed",
            "The model request failed.",
            raw,
            &["Test AI provider connection", "Check API key", "Change model", "Retry"],
        );
    }
    if lower.contains("eacces") || lower.contains("permission") || lower.contains("write") {
        return digest_error(
            "write_file_failed",
            "The report file could not be written.",
            raw,
            &["Check workspace permissions", "Choose another output folder", "Retry"],
        );
    }
    if lower.contains("connect") || lower.contains("connection") || lower.contains("401") || lower.contains("403") {
        return digest_error(
            "api_connection_failed",
            "The AI provider connection failed.",
            raw,
            &["Test AI provider connection", "Check API key and Base URL", "Retry"],
        );
    }
    digest_error("unknown", "Digest failed.", raw, &["Review the run log", "Check Settings", "Retry"])
}

fn digest_error(kind: &str, message: &str, raw: &str, actions: &[&str]) -> DigestError {
    DigestError {
        error_type: kind.to_string(),
        message: message.to_string(),
        raw: Some(raw.to_string()),
        suggested_actions: actions.iter().map(|value| value.to_string()).collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config() -> AppConfig {
        let workspace_path = std::env::temp_dir()
            .join("signalforge-daily-lib-tests")
            .to_string_lossy()
            .to_string();
        AppConfig {
            workspace_path: workspace_path.clone(),
            output_path: Path::new(&workspace_path)
                .join("reports")
                .to_string_lossy()
                .to_string(),
            ai_provider: AiProvider {
                provider: "iflow".to_string(),
                api_key: String::new(),
                base_url: None,
                model: "gpt-test".to_string(),
            },
            digest_defaults: DigestDefaults {
                language: "zh".to_string(),
                time_range_hours: 24,
                top_n: 6,
            },
            network: NetworkConfig {
                proxy_mode: "none".to_string(),
                http_proxy: None,
                https_proxy: None,
            },
            advanced: AdvancedConfig {
                feed_concurrency: None,
                ai_retries: None,
                max_ai_articles: None,
            },
            sources: Vec::new(),
            relevance_profile: RelevanceProfile::default(),
            automation: AutomationConfig::default(),
        }
    }

    #[test]
    fn preflight_failure_run_record_is_failed_with_trigger_and_error() {
        let config = test_config();

        let record = build_failed_preflight_run_record(
            &config,
            "scheduled",
            "API key is not configured",
        );

        assert_eq!(record.status, "failed");
        assert_eq!(record.trigger, "scheduled");
        assert_eq!(record.error.as_ref().unwrap().error_type, "missing_api_key");
        assert!(record.finished_at.is_some());
        assert!(record.output.as_ref().unwrap().log_path.is_some());
    }

    #[test]
    fn startup_missed_consumes_scheduled_slot_for_same_day() {
        let mut state = AutomationState::default();

        mark_startup_missed_consumed(&mut state, "2026-05-20", None);

        assert_eq!(state.last_startup_missed_date.as_deref(), Some("2026-05-20"));
        assert_eq!(state.last_scheduled_date.as_deref(), Some("2026-05-20"));
        assert!(state.last_skip_reason.is_none());
    }
}
