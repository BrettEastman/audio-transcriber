// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, AppHandle, path::BaseDirectory};
use std::process::{Command, Child};
use std::sync::Mutex;

struct BackendProcess(Mutex<Option<Child>>);

#[tauri::command]
fn start_backend(app_handle: AppHandle) -> Result<String, String> {
    let resource_path = app_handle
        .path()
        .resolve("main", BaseDirectory::Resource)
        .map_err(|e| format!("Failed to resolve backend path: {}", e))?;

    let mut child = Command::new(resource_path)
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    // Store the process handle
    let backend_state: tauri::State<BackendProcess> = app_handle.state();
    *backend_state.0.lock().unwrap() = Some(child);

    Ok("Backend started successfully".to_string())
}

fn main() {
    tauri::Builder::default()
        .manage(BackendProcess(Default::default()))
        .setup(|app| {
            // Auto-start backend on app launch
            let app_handle = app.handle();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_backend(app_handle.clone()) {
                    eprintln!("Failed to start backend: {}", e);
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| match event {
            tauri::WindowEvent::Destroyed => {
                // Clean up backend process when app closes
                let app_handle = window.app_handle();
                let backend_state: tauri::State<BackendProcess> = app_handle.state();
                if let Some(mut child) = backend_state.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![start_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}