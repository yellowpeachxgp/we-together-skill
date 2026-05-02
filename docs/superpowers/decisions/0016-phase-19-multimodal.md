# ADR 0016: Phase 19 — 多模态深化

## 状态

Accepted — 2026-04-19

## 背景

Phase 10 让真实文本数据源（iMessage / 微信 db / mbox / image / social）进入候选层。Phase 19 把音频 / 视频 / PDF / DOCX / 屏幕截图时序也纳入，凑齐"真人数字足迹"主要来源。

## 决策

### D1. AudioTranscriber Protocol

`llm/providers/audio.py` 提供 `AudioTranscriber` Protocol + `MockAudioTranscriber`（scripted） + `WhisperTranscriber`（延迟 import openai-whisper）。`importers/audio_importer.import_audio(path, transcriber)` 走与 image_importer 对称的形状（候选层优先）。

### D2. 视频走"分离输入"模式

`importers/video_importer.import_video(frames, audio_path, vision_client, audio_transcriber)` 不自己解视频容器，接受 `[(timestamp, frame_path), ...]` + 独立音轨路径。真实调用者用 ffmpeg 预处理。这让单元测试完全离线。

### D3. Document importer 延迟 import 三方依赖

`importers/document_importer.py` 支持 `.pdf`（pypdf）/ `.docx`（python-docx）/ `.txt` / `.md`。pypdf 与 python-docx 在真正读文件时才 import，未安装时给清晰错误信息。

### D4. 屏幕截图时序

`importers/screenshot_series_importer` 对每张截图调 `VisionLLMClient.describe_image`，产出按时间排序的 `screenshot_event` 序列。

### D5. 多模态 dedup

`services/evidence_dedup_service` 扩展三对 API：
- `compute_image_phash` / `is_duplicate_image` / `register_image_hash`
- `compute_audio_fingerprint` / `is_duplicate_audio` / `register_audio_hash`
- 公用 `phash_distance`（汉明距离）

内部走同一张 `evidence_hash_registry` 表，用 `img:` / `aud:` 前缀区分。极简实现（不依赖 PIL / librosa / chromaprint），真实场景可替换为专业库。

### D6. 统一候选层输出形状

所有新 importer 输出都是 `{identity_candidates, event_candidates, source, ...}`，与 Phase 10 一致，可直接喂给 `fusion_service.fuse_all`。

## 后果

### 正面
- 五类 importer 齐备，"数字分身" 能吃会议录音 / 工作文档 / 截图流
- 无外部依赖打底，CI / 测试永远稳定
- pHash 近似去重让同一截图二次导入不会膨胀事件表

### 负面 / 权衡
- 真实场景图像感知质量需要替换为 imagehash / blake3 等专业库
- 视频 importer 不解容器，集成时需要 ffmpeg 预处理步骤
- 音频 fingerprint 是 toy 实现，chromaprint 级别留到 Phase 22+

### 后续
- Phase 22：引入 imagehash / chromaprint 可选依赖
- 多模态 eval：多来源合并生成 memory 的质量评估
