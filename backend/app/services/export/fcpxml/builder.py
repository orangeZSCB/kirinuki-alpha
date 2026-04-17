import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from app.models.db import Project, ClipCandidate, Export
from app.services.export.fcpxml.timecode import TimecodeConverter
from app.core.config import settings
from fractions import Fraction

class FCPXMLBuilder:
    """FCPXML 1.13 构建器"""

    def __init__(self, db: Session):
        self.db = db

    async def build_and_save(self, project_id: str, export_id: str):
        """构建并保存 FCPXML"""
        try:
            # 获取项目和候选片段
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise Exception("项目不存在")

            candidates = self.db.query(ClipCandidate).filter(
                ClipCandidate.project_id == project_id,
                ClipCandidate.status.in_(["proposed", "kept"])
            ).order_by(ClipCandidate.start_seconds).all()

            if not candidates:
                raise Exception("没有候选片段")

            # 构建 FCPXML
            xml_content = self._build_fcpxml(project, candidates)

            # 保存文件
            export_path = settings.work_dir / "exports" / f"{project_id}_{export_id}.fcpxml"
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

            # 更新导出记录
            export = self.db.query(Export).filter(Export.id == export_id).first()
            if export:
                export.status = "completed"
                export.file_path = str(export_path)
                self.db.commit()

        except Exception as e:
            # 更新导出状态为失败
            export = self.db.query(Export).filter(Export.id == export_id).first()
            if export:
                export.status = "failed"
                export.export_metadata = {"error": str(e)}
                self.db.commit()
            raise

    def _build_fcpxml(self, project: Project, candidates: List[ClipCandidate]) -> str:
        """构建 FCPXML 内容"""
        # 创建根元素
        root = ET.Element("fcpxml", version="1.13")

        # 添加 resources
        resources = ET.SubElement(root, "resources")

        # 定义格式
        frame_rate = project.fps or 30.0
        frame_duration = Fraction(1, int(frame_rate))
        format_id = "r1"

        format_elem = ET.SubElement(
            resources,
            "format",
            name=f"FFVideoFormat{project.height}p{int(frame_rate)}",
            id=format_id,
            frameDuration=f"{frame_duration.numerator}/{frame_duration.denominator}s",
            width=str(project.width or 1920),
            height=str(project.height or 1080)
        )

        # 定义资源（源视频）
        asset_id = "r2"
        duration_frac = Fraction(int(project.duration_seconds * frame_rate), int(frame_rate))

        # 转换文件路径为 file:// URL
        video_path = Path(project.source_video_path).absolute()
        file_url = f"file://localhost{video_path.as_posix()}"

        asset_elem = ET.SubElement(
            resources,
            "asset",
            name=Path(project.source_video_path).name,
            id=asset_id,
            hasVideo="1",
            format=format_id,
            start="0/1s",
            duration=f"{duration_frac.numerator}/{duration_frac.denominator}s",
            hasAudio="1",
            audioChannels="2",
            audioSources="1"
        )

        media_rep = ET.SubElement(
            asset_elem,
            "media-rep",
            kind="original-media",
            src=file_url
        )

        # 创建 library 结构
        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", name="KiriNuki Exports")
        proj_elem = ET.SubElement(event, "project", name=project.name)

        # 计算总时长
        total_duration = sum(c.duration_seconds for c in candidates)
        total_duration_frac = Fraction(int(total_duration * frame_rate), int(frame_rate))

        sequence = ET.SubElement(
            proj_elem,
            "sequence",
            format=format_id,
            duration=f"{total_duration_frac.numerator}/{total_duration_frac.denominator}s",
            tcStart="0/1s",
            tcFormat="NDF"
        )

        spine = ET.SubElement(sequence, "spine")

        # 添加每个候选片段
        timeline_offset = 0.0
        for candidate in candidates:
            # 计算时间
            start_frac = Fraction(int(candidate.start_seconds * frame_rate), int(frame_rate))
            duration_frac = Fraction(int(candidate.duration_seconds * frame_rate), int(frame_rate))
            offset_frac = Fraction(int(timeline_offset * frame_rate), int(frame_rate))

            clip_name = candidate.title or f"片段 {candidate.start_seconds:.1f}s"

            asset_clip = ET.SubElement(
                spine,
                "asset-clip",
                ref=asset_id,
                name=clip_name,
                offset=f"{offset_frac.numerator}/{offset_frac.denominator}s",
                start=f"{start_frac.numerator}/{start_frac.denominator}s",
                duration=f"{duration_frac.numerator}/{duration_frac.denominator}s"
            )

            # 如果有备注，添加 note
            if candidate.summary:
                note = ET.SubElement(asset_clip, "note")
                note.text = candidate.summary

            timeline_offset += candidate.duration_seconds

        # 格式化 XML
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="    ", encoding="UTF-8").decode("utf-8")

        # 添加 DOCTYPE
        lines = pretty_xml.split("\n")
        lines.insert(1, '<!DOCTYPE fcpxml>')
        return "\n".join(lines)
