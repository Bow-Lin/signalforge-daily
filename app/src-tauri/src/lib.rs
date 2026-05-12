use chrono::{DateTime, Local, Utc};
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
};
use tauri::{AppHandle, Emitter, State};

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
struct AppSnapshot {
    config: Option<AppConfig>,
    runs: Vec<RunRecord>,
    reports: Vec<ReportRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunRecord {
    id: String,
    #[serde(rename = "type")]
    run_type: String,
    status: String,
    started_at: String,
    finished_at: Option<String>,
    duration_ms: Option<i64>,
    params_snapshot: ParamsSnapshot,
    stats: Option<RunStats>,
    output: Option<RunOutput>,
    top_picks: Option<Vec<TopPick>>,
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
struct TopPick {
    title: String,
    source: Option<String>,
    url: Option<String>,
    published_at: Option<String>,
    reason: Option<String>,
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
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![
            get_snapshot,
            choose_folder,
            save_config,
            test_connection,
            generate_digest,
            read_markdown,
            open_path,
            reveal_path,
            delete_run
        ])
        .run(tauri::generate_context!())
        .expect("error while running AI News Collection");
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

    let mut command = Command::new("uv");
    command
        .arg("run")
        .arg("python")
        .arg("-c")
        .arg(script)
        .current_dir(repo_root()?);
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
    let config = load_config()?.ok_or_else(|| "Workspace is not configured".to_string())?;
    if config.ai_provider.api_key.trim().is_empty() {
        return Err("API key is not configured".to_string());
    }

    {
        let mut active = state
            .active_run
            .lock()
            .map_err(|_| "Unable to lock run state".to_string())?;
        if *active {
            return Err("Digest generation is already running".to_string());
        }
        *active = true;
    }

    ensure_workspace_dirs(&config)?;
    let started = Utc::now();
    let timestamp = started.format("%Y%m%d-%H%M%S").to_string();
    let run_id = format!("run-{}", timestamp);
    let report_path = Path::new(&config.output_path).join(format!("digest-{}.md", timestamp));
    let log_path = logs_dir(&config).join(format!("{}.log", run_id));

    let record = RunRecord {
        id: run_id.clone(),
        run_type: "digest".to_string(),
        status: "running".to_string(),
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
        error: None,
    };

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

    let active_run = state.active_run.clone();
    let record_for_worker = record.clone();
    thread::spawn(move || {
        let _ = run_digest_process(app, config, record_for_worker, report_path, log_path);
        if let Ok(mut active) = active_run.lock() {
            *active = false;
        }
    });

    Ok(record)
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

    let mut command = digest_command(&config, &report_path)?;
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

    if status.success() && report_path.exists() {
        let markdown = fs::read_to_string(&report_path).unwrap_or_default();
        record.status = "success".to_string();
        record.top_picks = Some(parse_top_picks(&markdown));
        record.stats = parse_stats(&raw);
        save_run(&config, &record)?;
        emit(
            &app,
            DigestEvent::Progress {
                run_id: run_id.clone(),
                step: "Completed".to_string(),
                message: "Digest generated successfully.".to_string(),
            },
        );
        emit(&app, DigestEvent::Completed { run_id, record });
    } else {
        let error = classify_digest_error(&raw);
        record.status = "failed".to_string();
        record.error = Some(error);
        save_run(&config, &record)?;
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

fn digest_command(config: &AppConfig, report_path: &Path) -> Result<Command, String> {
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
    ];
    if let Some(base_url) = config.ai_provider.base_url.as_ref().filter(|value| !value.trim().is_empty()) {
        args.push("--iflow-base-url".to_string());
        args.push(base_url.clone());
    }

    let sidecar = env::var("NEWS_COLLECTION_DIGEST_SIDECAR").ok().filter(|value| !value.trim().is_empty());
    let mut command = if let Some(path) = sidecar {
        let mut cmd = Command::new(path);
        cmd.args(args);
        cmd
    } else {
        let mut cmd = Command::new("uv");
        cmd.arg("run")
            .arg("python")
            .arg("-m")
            .arg("news_collection.digest_cli")
            .args(args);
        cmd
    };

    command.current_dir(repo_root()?);
    apply_env(&mut command, config);
    Ok(command)
}

fn apply_env(command: &mut Command, config: &AppConfig) {
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

fn snapshot() -> Result<AppSnapshot, String> {
    let config = load_config()?;
    let runs = config.as_ref().map(read_runs).transpose()?.unwrap_or_default();
    let reports = config
        .as_ref()
        .map(|cfg| read_reports(cfg, &runs))
        .transpose()?
        .unwrap_or_default();
    Ok(AppSnapshot { config, runs, reports })
}

fn load_config() -> Result<Option<AppConfig>, String> {
    let pointer_path = pointer_config_path()?;
    if pointer_path.exists() {
        let pointer: serde_json::Value = read_json(&pointer_path)?;
        if let Some(workspace) = pointer.get("workspacePath").and_then(|value| value.as_str()) {
            let workspace_config = Path::new(workspace).join("app-config.json");
            if workspace_config.exists() {
                return read_json(&workspace_config).map(Some);
            }
        }
    }
    Ok(None)
}

fn persist_config(config: &AppConfig) -> Result<(), String> {
    ensure_workspace_dirs(config)?;
    write_json(&Path::new(&config.workspace_path).join("app-config.json"), config)?;
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
    fs::create_dir_all(logs_dir(config)).map_err(|err| err.to_string())
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
        .join("ai-news-collection");
    Ok(dir.join("workspace-pointer.json"))
}

fn runs_dir(config: &AppConfig) -> PathBuf {
    Path::new(&config.workspace_path).join("runs")
}

fn logs_dir(config: &AppConfig) -> PathBuf {
    Path::new(&config.workspace_path).join("logs")
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
    let regex = Regex::new(r"Stats:\s*(\d+)\s+sources\s+→\s+(\d+)\s+articles\s+→\s+(\d+)\s+recent\s+→\s+(\d+)\s+selected").ok()?;
    let caps = regex.captures(raw)?;
    Some(RunStats {
        sources_scanned: caps.get(1).and_then(|value| value.as_str().parse().ok()),
        articles_fetched: caps.get(2).and_then(|value| value.as_str().parse().ok()),
        articles_selected: caps.get(4).and_then(|value| value.as_str().parse().ok()),
    })
}

fn parse_top_picks(markdown: &str) -> Vec<TopPick> {
    let section = markdown
        .split("## 🏆 今日必读")
        .nth(1)
        .and_then(|value| value.split("---").next())
        .unwrap_or("");
    let Ok(regex) = Regex::new(r"(?s)(?:🥇|🥈|🥉)\s+\*\*(?P<title>.+?)\*\*.*?\[(?P<original>.+?)\]\((?P<url>.+?)\)\s+—\s+(?P<source>.+?)\s+·.*?(?:💡 \*\*为什么值得读\*\*: (?P<reason>.+?)\n)?") else {
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
