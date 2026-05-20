# Manual Smoke Test

Run this checklist before tagging or publishing a release.

## Fresh Install

- [ ] Install the Windows x64 installer from `app/src-tauri/target/release/bundle/`.
- [ ] Launch SignalForge Daily from Start Menu or installer finish screen.
- [ ] Confirm the window title is `SignalForge Daily`.
- [ ] Confirm no terminal window is required for normal use.

## First Run

- [ ] With no existing workspace pointer, app enters Setup.
- [ ] Choose a fresh workspace.
- [ ] Enter API Key, Base URL, and Model.
- [ ] Click `测试连接`.
- [ ] Save and enter Today.

## Demo Mode

- [ ] From Setup, click `进入 Demo Mode`.
- [ ] Today shows a sample digest and a Demo banner.
- [ ] Reports previews the sample Markdown report.
- [ ] Sources shows sample healthy, noisy, and failed source quality states.
- [ ] Copy Markdown works for the sample report.
- [ ] Clear Demo Mode returns to Setup or the real workspace.

## Digest Flow

- [ ] Click `生成今日摘要`.
- [ ] Progress reaches Completed.
- [ ] RunRecord is created.
- [ ] Top Picks appear.
- [ ] Full report opens in Reports preview.
- [ ] Open file / reveal in folder works.
- [ ] Logs folder can be opened.

## Source Quality

- [ ] Disable one source.
- [ ] Save persists after app restart.
- [ ] Re-enable the source.
- [ ] Add a test RSS source.
- [ ] Sources overview metrics update.

## Relevance Profile

- [ ] Add an interested topic.
- [ ] Add a muted topic.
- [ ] Change preferred content types.
- [ ] Save and restart.
- [ ] Settings restore the saved profile.

## Automation

- [ ] Enable automation.
- [ ] Set run time a few minutes in the future.
- [ ] Confirm next run time appears.
- [ ] Wait for scheduled run while the app is open.
- [ ] Confirm RunRecord trigger is scheduled.
- [ ] Confirm skip-if-generated-today behavior.
- [ ] Test notification permission.
- [ ] Confirm success or failure notification appears.

## Diagnostics

- [ ] Settings > About shows app name, version, build date, platform, workspace, and logs path.
- [ ] `打开 logs folder` opens the workspace logs directory.
- [ ] `复制诊断信息` copies diagnostic text.
- [ ] Diagnostic text does not include API Key, token, or full secret config.

## Installer Cleanup

- [ ] Quit the app.
- [ ] Uninstall from Windows Apps settings.
- [ ] Confirm the app is removed.
- [ ] Confirm user workspace data remains user-owned and can be deleted manually.
