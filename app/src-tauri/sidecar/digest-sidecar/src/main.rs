use std::{
    env,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let repo_root = env::var("NEWS_COLLECTION_REPO_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| infer_repo_root());

    let status = Command::new("uv")
        .arg("run")
        .arg("python")
        .arg("-m")
        .arg("news_collection.digest_cli")
        .args(args)
        .current_dir(repo_root)
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

fn infer_repo_root() -> PathBuf {
    let mut current = env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
    for _ in 0..8 {
        if current.join("pyproject.toml").exists() && current.join("src").join("news_collection").exists() {
            return current;
        }
        if !current.pop() {
            break;
        }
    }
    Path::new(".").to_path_buf()
}
