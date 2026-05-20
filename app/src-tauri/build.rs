fn main() {
    let build_date = std::env::var("SIGNALFORGE_BUILD_DATE").unwrap_or_else(|_| "development".to_string());
    println!("cargo:rustc-env=SIGNALFORGE_BUILD_DATE={build_date}");
    tauri_build::build();
}
