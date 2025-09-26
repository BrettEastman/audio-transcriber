// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, AppHandle};
use tauri_plugin_shell::{ShellExt, process::CommandEvent};
use std::sync::Mutex;
use std::net::TcpStream;

struct BackendProcess(Mutex<Option<tauri_plugin_shell::process::CommandChild>>);

fn is_backend_listening() -> bool {
    TcpStream::connect("127.0.0.1:8000").is_ok()
}

#[tauri::command]
fn start_backend(app_handle: AppHandle) -> Result<String, String> {
    println!("Attempting to start backend sidecar...");

    // If port 8000 already has a listener, don't spawn another backend
    if is_backend_listening() {
        println!("Backend already listening on 127.0.0.1:8000; skipping spawn.");
        return Ok("Backend already running".to_string());
    }

    // Also avoid double-spawn if we already have a child stored
    let backend_state: tauri::State<BackendProcess> = app_handle.state();
    if backend_state.0.lock().unwrap().is_some() {
        println!("Backend process already spawned; skipping spawn.");
        return Ok("Backend already spawned".to_string());
    }

    // Ensure Homebrew and common bin dirs are on PATH when launching sidecar
    let mut path = std::env::var("PATH").unwrap_or_default();
    let brew_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"];
    // Prepend any that are missing
    for p in brew_paths {
        if !path.split(':').any(|s| s == p) {
            path = format!("{}:{}", p, path);
        }
    }
    println!("Starting backend with PATH={}", path);

    let sidecar_command = app_handle.shell().sidecar("main_with_assets")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .env("PATH", path);

    let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("Failed to spawn backend sidecar: {}", e))?;

    // Store the process handle
    *backend_state.0.lock().unwrap() = Some(child);

    // Handle stdout/stderr in background
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    println!("Backend stdout: {}", line);
                }
                CommandEvent::Stderr(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    eprintln!("Backend stderr: {}", line);
                }
                CommandEvent::Error(error) => {
                    eprintln!("Backend error: {}", error);
                }
                CommandEvent::Terminated(payload) => {
                    println!("Backend terminated with code: {:?}", payload.code);
                    break;
                }
                _ => {
                    // Handle any future CommandEvent variants
                    println!("Received unknown command event");
                }
            }
        }
    });

    Ok("Backend started successfully".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Default::default()))
        .setup(|app| {
            // Auto-start backend on app launch
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_backend(app_handle) {
                    eprintln!("Failed to start backend: {}", e);
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Clean up backend process when app closes
                let app_handle = window.app_handle();
                let backend_state: tauri::State<BackendProcess> = app_handle.state();
                let mutex = &backend_state.0;
                let mut guard = mutex.lock().unwrap();
                if let Some(child) = guard.take() {
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![start_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");

}