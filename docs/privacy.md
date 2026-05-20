# Privacy and Local Data

SignalForge Daily is designed as a local-first desktop app. Your reports, run records, source settings, feedback, and logs live in the workspace folder you choose.

## Local Data

The selected workspace stores:

```text
app-config.json
runs/
reports/
logs/
metadata/
```

- `app-config.json`: workspace path, output path, provider settings, source list, relevance profile, automation settings.
- `runs/`: one JSON RunRecord per digest run.
- `reports/`: generated Markdown digest reports.
- `logs/`: stdout / stderr logs from digest runs.
- `metadata/`: source run stats, item feedback, automation skip state.

## API Key Storage

The desktop app stores the configured API key in local `app-config.json`. It is not committed by this repository and is not uploaded to a SignalForge Daily server.

Do not share your workspace folder if it contains a real API key. The About page diagnostic copy intentionally excludes API key, token, and full secret config values.

## Requests Sent to AI Provider

When generating a digest, SignalForge Daily sends article metadata and prompts to the configured OpenAI-compatible provider. This can include:

- article title
- article description / excerpt
- source name
- source URL or original URL
- relevance profile topics
- scoring and summarization instructions

Full local run logs and reports are not sent to SignalForge Daily-owned servers.

## Own Servers

SignalForge Daily currently does not operate a backend service for syncing, telemetry, accounts, or cloud storage. The app does not upload your workspace, reports, logs, sources, feedback, or API key to a SignalForge Daily server.

Optional third-party AI Provider requests happen only when you run connection tests or generate digests.

## Delete Local Data

To delete local data:

1. Open Settings and note the Workspace path.
2. Quit SignalForge Daily.
3. Delete the workspace folder or remove specific subfolders such as `runs/`, `reports/`, `logs/`, and `metadata/`.
4. Delete the workspace pointer from the OS config directory if you want the app to forget the workspace.

On Windows, the pointer is typically under:

```text
%APPDATA%\signalforge-daily\workspace-pointer.json
```

## Export Reports

Reports are Markdown files under the configured output folder, usually:

```text
<workspace>\reports\
```

You can copy, archive, or version those files directly. Reports do not require the app to be opened.
