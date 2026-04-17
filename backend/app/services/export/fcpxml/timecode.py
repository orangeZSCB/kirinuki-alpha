from fractions import Fraction

class TimecodeConverter:
    """时间码转换器"""

    @staticmethod
    def seconds_to_fraction(seconds: float, frame_rate: float = 30.0) -> Fraction:
        """将秒转换为分数"""
        # 转换为帧数
        frames = round(seconds * frame_rate)
        return Fraction(frames, int(frame_rate))

    @staticmethod
    def fraction_to_fcpxml(frac: Fraction) -> str:
        """将分数转换为 FCPXML 时间格式"""
        return f"{frac.numerator}/{frac.denominator}s"

    @staticmethod
    def seconds_to_fcpxml(seconds: float, frame_rate: float = 30.0) -> str:
        """将秒直接转换为 FCPXML 格式"""
        frac = TimecodeConverter.seconds_to_fraction(seconds, frame_rate)
        return TimecodeConverter.fraction_to_fcpxml(frac)
