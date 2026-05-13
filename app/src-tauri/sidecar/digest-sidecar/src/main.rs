use std::{
    env,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let repo_root = env::var("SIGNALFORGE_DAILY_REPO_ROOT")
        .or_else(|_| env::var("NEWS_COLLECTION_REPO_ROOT"))
        .map(PathBuf::from)
        .unwrap_or_else(|_| infer_repo_root());

    let mut command = python_command(&repo_root);
    let status = command
        .arg("-m")
        .arg("signalforge_daily.digest_cli")
        .args(args)
        .current_dir(&repo_root)
        .status();

    match status {
        Ok(status) if status.success() => ExitCode::SUCCESS,
        Ok(status) => ExitCode::from(status.code().unwrap_or(1) as u8),
        Err(err) => {
            eprintln!("failed to start Python digest backend: {err}");
            ExitCode::from(1)
        }
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

fn infer_repo_root() -> PathBuf {
    let mut current = env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
    for _ in 0..8 {
        if current.join("pyproject.toml").exists() && current.join("src").join("signalforge_daily").exists() {
            return current;
        }
        if !current.pop() {
            break;
        }
    }
    Path::new(".").to_path_buf()
}
