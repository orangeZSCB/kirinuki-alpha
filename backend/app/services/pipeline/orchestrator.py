from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.db import Project, ProjectRun, PipelineStep, TranscriptSegment, AnalysisChunk, ClipCandidate, ProviderConfig
from app.services.ffmpeg_service import FFmpegService
from app.services.transcription.local import LocalWhisperProvider
from app.services.transcription.remote import RemoteWhisperProvider
from app.services.transcription.gpt_sovits import GPTSoVITSProvider
from app.services.analysis.chunker import Chunker
from app.services.analysis.audio_features import AudioFeatureExtractor
from app.services.analysis.cheap_ranker import CheapRanker
from app.services.analysis.multimodal_ranker import MultimodalRanker
from app.services.analysis.multimodal_analyzer import MultimodalAnalyzer
from app.core.config import settings
import base64
import logging

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """Pipeline 编排器"""

    def __init__(self, db: Session):
        self.db = db
        self.ffmpeg = FFmpegService()

    async def run_pipeline(self, project_id: str, run_id: str):
        """运行完整 pipeline（支持断点续跑）"""
        try:
            logger.info(f"========================================")
            logger.info(f"🚀 开始运行 Pipeline")
            logger.info(f"项目 ID: {project_id}")
            logger.info(f"运行 ID: {run_id}")
            logger.info(f"========================================")

            # 更新 run 状态
            run = self.db.query(ProjectRun).filter(ProjectRun.id == run_id).first()

            # 如果是首次运行，设置状态
            if run.status == "pending":
                run.status = "running"
                run.started_at = datetime.utcnow()
                self.db.commit()
            elif run.status == "failed":
                # 断点续跑：从失败的地方继续
                logger.info(f"⚠️  检测到失败的运行，将从断点继续...")
                run.status = "running"
                run.error_message = None
                self.db.commit()

            # 定义所有步骤
            steps = [
                ("ingest", "📥 [步骤 1/4] 素材导入", self._step_ingest),
                ("transcribe", "🎤 [步骤 2/4] 语音转录", self._step_transcribe),
                ("extract_features", "🎵 [步骤 3/4] 提取音频特征", self._step_extract_features),
                ("multimodal_review", "🎬 [步骤 4/4] 多模态分析（整个视频）", self._step_multimodal_review),
            ]

            # 执行各个步骤（跳过已完成的）
            for step_name, step_label, step_func in steps:
                # 检查步骤是否已完成
                existing_step = self.db.query(PipelineStep).filter(
                    PipelineStep.run_id == run_id,
                    PipelineStep.step_name == step_name
                ).first()

                if existing_step and existing_step.status == "completed":
                    logger.info(f"\n✅ {step_label} - 已完成，跳过")
                    continue

                logger.info(f"\n{step_label}")
                await step_func(project_id, run_id)

            # 完成
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"\n========================================")
            logger.info(f"✅ Pipeline 完成！")
            logger.info(f"========================================")

        except Exception as e:
            logger.error(f"\n❌ Pipeline 失败: {str(e)}", exc_info=True)
            run = self.db.query(ProjectRun).filter(ProjectRun.id == run_id).first()
            run.status = "failed"
            run.error_message = str(e)
            run.finished_at = datetime.utcnow()
            self.db.commit()
            raise

    async def _step_ingest(self, project_id: str, run_id: str):
        """步骤 1: 素材导入"""
        step = self._create_step(run_id, "ingest")

        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            logger.info(f"  📹 视频路径: {project.source_video_path}")

            # 获取视频元信息
            logger.info(f"  🔍 正在探测视频信息...")
            video_info = self.ffmpeg.probe_video(project.source_video_path)
            logger.info(f"  ✓ 时长: {video_info['duration']:.1f}秒")
            logger.info(f"  ✓ 分辨率: {video_info['width']}x{video_info['height']}")
            logger.info(f"  ✓ 帧率: {video_info['fps']:.2f} fps")

            # 更新项目信息
            project.duration_seconds = video_info["duration"]
            project.fps = video_info["fps"]
            project.width = video_info["width"]
            project.height = video_info["height"]
            project.status = "processing"

            # 提取音频
            audio_path = settings.work_dir / "projects" / project_id / "audio.wav"
            logger.info(f"  🎵 正在提取音频到: {audio_path}")
            self.ffmpeg.extract_audio(project.source_video_path, str(audio_path))
            project.audio_path = str(audio_path)
            logger.info(f"  ✓ 音频提取完成")

            self.db.commit()

            step.status = "completed"
            step.finished_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"  ✅ 素材导入完成")

        except Exception as e:
            logger.error(f"  ❌ 素材导入失败: {str(e)}")
            step.status = "failed"
            step.error_message = str(e)
            self.db.commit()
            raise

    async def _step_transcribe(self, project_id: str, run_id: str):
        """步骤 2: 转录"""
        step = self._create_step(run_id, "transcribe")

        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            logger.info(f"  🎤 音频路径: {project.audio_path}")

            # 检查是否已有转录数据
            existing_segments = self.db.query(TranscriptSegment).filter(
                TranscriptSegment.project_id == project_id
            ).count()

            if existing_segments > 0:
                logger.info(f"  ✓ 检测到已有 {existing_segments} 个转录片段，跳过转录")
                step.status = "completed"
                step.finished_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"  ✅ 转录完成（使用已有数据）")
                return

            # 获取 Whisper 配置
            logger.info(f"  🔍 正在查找 Whisper 配置...")
            whisper_config = self.db.query(ProviderConfig).filter(
                ProviderConfig.provider_kind == "whisper",
                ProviderConfig.is_default == True
            ).first()

            if not whisper_config:
                raise Exception("未配置 Whisper Provider")

            logger.info(f"  ✓ 找到配置: {whisper_config.config.get('mode', 'remote')} 模式")

            # 解密 API Key
            config = whisper_config.config.copy()
            if "api_key" in config:
                config["api_key"] = base64.b64decode(config["api_key"]).decode()

            # 选择 Provider
            mode = config.get("mode", "remote")
            if mode == "local":
                logger.info(f"  🖥️  使用本地 Whisper")
                provider = LocalWhisperProvider(config)
            elif mode == "gpt_sovits":
                logger.info(f"  🎵 使用 GPT-SoVITS API: {config.get('base_url')}")
                provider = GPTSoVITSProvider(config)
            else:
                logger.info(f"  ☁️  使用远程 Whisper API: {config.get('base_url')}")
                provider = RemoteWhisperProvider(config)

            # 转录
            logger.info(f"  🎙️  开始转录...")
            segments = await provider.transcribe(project.audio_path, project.language)
            logger.info(f"  ✓ 转录完成，得到 {len(segments)} 个片段")

            # 保存到数据库
            logger.info(f"  💾 正在保存到数据库...")
            for seg in segments:
                db_seg = TranscriptSegment(
                    project_id=project_id,
                    start_seconds=seg.start,
                    end_seconds=seg.end,
                    text=seg.text
                )
                self.db.add(db_seg)

            self.db.commit()
            logger.info(f"  ✓ 已保存 {len(segments)} 个片段")

            # 如果是 GPT-SoVITS，额外保存 SRT 文件
            if mode == "gpt_sovits" and isinstance(provider, GPTSoVITSProvider):
                srt_path = settings.work_dir / "projects" / project_id / "transcription.srt"
                logger.info(f"  💾 正在保存 SRT 字幕文件...")
                provider.save_srt(segments, str(srt_path))
                logger.info(f"  ✓ SRT 文件已保存: {srt_path}")

            step.status = "completed"
            step.finished_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"  ✅ 转录完成")

        except Exception as e:
            logger.error(f"  ❌ 转录失败: {str(e)}", exc_info=True)
            step.status = "failed"
            step.error_message = str(e)
            self.db.commit()
            raise

    async def _step_extract_features(self, project_id: str, run_id: str):
        """步骤 3: 提取音频特征"""
        step = self._create_step(run_id, "extract_features")

        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            logger.info(f"  🎵 正在分析音频特征...")

            # 提取特征
            features = AudioFeatureExtractor.extract_features(project.audio_path)
            logger.info(f"  ✓ 特征提取完成")
            logger.info(f"  ✓ 音量峰值数: {len(features.get('volume_peaks', []))}")
            logger.info(f"  ✓ 平均音量: {features.get('avg_volume', 0):.2f}")

            # 保存到步骤输出
            step.output_data = features
            step.status = "completed"
            step.finished_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"  ✅ 音频特征提取完成")

        except Exception as e:
            logger.error(f"  ❌ 特征提取失败: {str(e)}")
            step.status = "failed"
            step.error_message = str(e)
            self.db.commit()
            raise

    async def _step_chunk_and_screen(self, project_id: str, run_id: str):
        """步骤 4: 分块和初筛"""
        step = self._create_step(run_id, "chunk_and_screen")

        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            logger.info(f"  📊 视频时长: {project.duration_seconds:.1f}秒")

            # 创建块
            logger.info(f"  🔨 正在创建分析块...")
            chunks = Chunker.create_chunks(project.duration_seconds)
            logger.info(f"  ✓ 创建了 {len(chunks)} 个分析块（每块 5 分钟）")

            # 获取转录文本
            logger.info(f"  📖 正在加载转录片段...")
            segments = self.db.query(TranscriptSegment).filter(
                TranscriptSegment.project_id == project_id
            ).all()
            logger.info(f"  ✓ 加载了 {len(segments)} 个转录片段")

            # 为每个块打分（简化版，只用文本）
            logger.info(f"  🔍 正在为每个块打分...")

            for idx, (start, end) in enumerate(chunks):
                try:
                    if (idx + 1) % 5 == 0 or idx == 0:
                        logger.info(f"    处理进度: {idx + 1}/{len(chunks)}")

                    # 获取该块的转录文本
                    chunk_text = " ".join([
                        seg.text for seg in segments
                        if seg.start_seconds >= start and seg.end_seconds <= end
                    ])

                    # 简单打分：只用文本长度
                    text_score = min(len(chunk_text) / 1000.0, 1.0)  # 归一化到 0-1

                    # 保存块
                    chunk = AnalysisChunk(
                        project_id=project_id,
                        chunk_index=idx,
                        start_seconds=start,
                        end_seconds=end,
                        transcript_summary=chunk_text[:500] if chunk_text else "",
                        heuristic_score=0.0,  # 暂时不用音频特征
                        cheap_model_score=text_score,
                        selected_for_mm=False,
                        feature_data={"text_length": len(chunk_text)}
                    )
                    self.db.add(chunk)

                    # 每 10 个块提交一次
                    if (idx + 1) % 10 == 0:
                        self.db.commit()

                except Exception as e:
                    logger.error(f"    ❌ 处理块 {idx + 1} 失败: {str(e)}")
                    continue

            # 最终提交
            self.db.commit()
            logger.info(f"  ✅ 分块和初筛完成，共 {len(chunks)} 个块")

            step.status = "completed"
            step.finished_at = datetime.utcnow()
            step.output_data = {"num_chunks": len(chunks)}
            self.db.commit()

        except Exception as e:
            logger.error(f"  ❌ 分块失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            step.status = "failed"
            step.error_message = str(e)
            self.db.commit()
            raise

    async def _step_generate_candidates(self, project_id: str, run_id: str):
        """步骤 5: 生成候选片段"""
        step = self._create_step(run_id, "generate_candidates")

        try:
            logger.info(f"  ✨ 正在选择高分块...")
            # 获取高分块
            chunks = self.db.query(AnalysisChunk).filter(
                AnalysisChunk.project_id == project_id
            ).order_by(AnalysisChunk.cheap_model_score.desc()).limit(15).all()

            logger.info(f"  ✓ 选出了 {len(chunks)} 个高分块")

            # 标记为需要多模态复审
            for i, chunk in enumerate(chunks):
                chunk.selected_for_mm = True

                # 创建候选片段（扩展时间范围）
                start = max(0, chunk.start_seconds - 15)
                end = chunk.end_seconds + 20
                duration = end - start

                candidate = ClipCandidate(
                    project_id=project_id,
                    start_seconds=start,
                    end_seconds=end,
                    duration_seconds=duration,
                    heuristic_score=chunk.heuristic_score,
                    cheap_model_score=chunk.cheap_model_score,
                    status="proposed"
                )
                self.db.add(candidate)
                logger.info(f"  ✓ 候选片段 {i+1}: {start:.1f}s - {end:.1f}s (得分: {chunk.cheap_model_score:.2f})")

            self.db.commit()

            step.status = "completed"
            step.finished_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"  ✅ 候选片段生成完成")

        except Exception as e:
            logger.error(f"  ❌ 候选片段生成失败: {str(e)}")
            step.status = "failed"
            step.error_message = str(e)
            self.db.commit()
            raise

    async def _step_multimodal_review(self, project_id: str, run_id: str):
        """步骤 6: 多模态复审 - 重写版本"""
        step = self._create_step(run_id, "multimodal_review")

        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()

            # 获取多模态配置
            logger.info(f"  🔍 正在查找多模态配置...")
            mm_config = self.db.query(ProviderConfig).filter(
                ProviderConfig.provider_kind == "multimodal",
                ProviderConfig.is_default == True
            ).first()

            if not mm_config:
                logger.info(f"  ⚠️  未配置多模态 Provider，跳过此步骤")
                step.status = "completed"
                step.finished_at = datetime.utcnow()
                self.db.commit()
                return

            logger.info(f"  ✓ 找到多模态配置")

            # 解密 API Key
            config = mm_config.config.copy()
            if "api_key" in config:
                config["api_key"] = base64.b64decode(config["api_key"]).decode()

            # 创建新的多模态分析器
            analyzer = MultimodalAnalyzer(config)

            # 获取所有转录片段
            logger.info(f"  📝 正在加载转录文本...")
            transcript_segments = self.db.query(TranscriptSegment).filter(
                TranscriptSegment.project_id == project_id
            ).order_by(TranscriptSegment.start_seconds).all()

            transcript_data = [
                {
                    "text": seg.text,
                    "start": seg.start_seconds,
                    "end": seg.end_seconds
                }
                for seg in transcript_segments
            ]
            logger.info(f"  ✓ 加载了 {len(transcript_data)} 个转录片段")

            # 调用多模态分析器（两阶段分析）
            logger.info(f"  🤖 正在调用多模态模型分析整个视频...")
            logger.info(f"  ⏱️  这可能需要较长时间，请耐心等待...")

            result = await analyzer.analyze_full_video(
                transcript_segments=transcript_data,
                video_path=project.source_video_path,
                video_duration=project.duration_seconds,
                ffmpeg_service=self.ffmpeg
            )

            logger.info(f"  ✓ 多模态分析完成")
            logger.info(f"\n" + "="*60)
            logger.info(f"📊 分析报告（Markdown）：")
            logger.info(f"="*60)
            logger.info(result["markdown_summary"])
            logger.info(f"="*60)

            # 删除旧的候选片段
            logger.info(f"  🗑️  清除旧的候选片段...")
            self.db.query(ClipCandidate).filter(
                ClipCandidate.project_id == project_id
            ).delete()
            self.db.commit()

            # 创建新的候选片段
            logger.info(f"  ✨ 正在创建 {len(result['clips'])} 个候选片段...")
            for i, clip in enumerate(result["clips"]):
                candidate = ClipCandidate(
                    project_id=project_id,
                    start_seconds=clip.start_time,
                    end_seconds=clip.end_time,
                    duration_seconds=clip.end_time - clip.start_time,
                    title=clip.title,
                    tags=clip.tags,
                    multimodal_score=clip.score,
                    final_score=clip.score,  # 直接使用多模态评分
                    status="proposed",
                    summary=clip.reason  # 使用 reason 作为 summary
                )
                self.db.add(candidate)
                logger.info(f"  ✓ [{i+1}] {clip.start_time:.1f}s-{clip.end_time:.1f}s | 评分: {clip.score:.1f} | {clip.title}")

            self.db.commit()

            # 保存分析报告到文件
            report_path = settings.work_dir / "projects" / project_id / "analysis_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(result["markdown_summary"])
            logger.info(f"  💾 分析报告已保存到: {report_path}")

            step.status = "completed"
            step.finished_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"  ✅ 多模态复审完成")

        except Exception as e:
            logger.error(f"  ❌ 多模态复审失败: {str(e)}", exc_info=True)
            step.status = "failed"
            step.error_message = str(e)
            self.db.commit()
            raise

    def _create_step(self, run_id: str, step_name: str) -> PipelineStep:
        """创建 pipeline 步骤"""
        step = PipelineStep(
            run_id=run_id,
            step_name=step_name,
            status="running",
            started_at=datetime.utcnow()
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step
