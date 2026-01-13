# fusion/adaptive_fusion.py

class AdaptiveFusion:
    """
    2센서 적응형 융합 (초음파 제외)
    """

    def __init__(self):
        # Threshold
        self.snr_threshold = 15.0  # dB

        # 가중치 (2센서)
        self.weights_audio_trust = {
            'audio': 0.70,  # 음향 신뢰 시
            'gap': 0.30
        }

        self.weights_visual_trust = {
            'audio': 0.30,  # 시각 신뢰 시
            'gap': 0.70
        }

    def fuse(self, audio_data, gaps):
        """
        Args:
            audio_data: {angle, snr, confidence, raw_angle}
            gaps: [{start, end, center, width, angle, confidence}, ...]

        Returns:
            {
                'best_gap': gap dict,
                'mode': 'audio_trust' or 'visual_trust',
                'score': float,
                'all_scores': [...]
            }
        """

        if not gaps or not audio_data:
            return None

        # === 1. 모드 판단 ===
        if audio_data['snr'] >= self.snr_threshold:
            mode = "audio_trust"
            weights = self.weights_audio_trust
        else:
            mode = "visual_trust"
            weights = self.weights_visual_trust

        print(f"\n{'=' * 60}")
        print(f"🎯 모드: {mode}")
        print(f"   SNR: {audio_data['snr']:.1f}dB (threshold: {self.snr_threshold})")
        print(f"   음향 방향: {audio_data['angle']:.1f}° (보정됨)")
        print(f"   가중치: 음향 {weights['audio']:.0%} + 틈 {weights['gap']:.0%}")
        print(f"{'=' * 60}")

        # === 2. 각 틈 점수 계산 ===
        gap_scores = []

        for i, gap in enumerate(gaps):
            # 음향 점수
            angle_diff = abs(gap['angle'] - audio_data['angle'])
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            audio_score = max(0, 1.0 - (angle_diff / 90.0))

            # SNR 보정
            snr_factor = min(1.0, max(0.5, audio_data['snr'] / 30.0))
            audio_score *= snr_factor

            # 틈 점수 (크기 + 신뢰도)
            size_score = min(1.0, gap['width'] / 300.0)
            gap_score = (size_score + gap['confidence']) / 2.0

            # 최종 점수
            total_score = (
                    audio_score * weights['audio'] +
                    gap_score * weights['gap']
            )

            gap_scores.append({
                'gap': gap,
                'audio_score': audio_score,
                'gap_score': gap_score,
                'total_score': total_score
            })

            print(f"\n틈 #{i} (각도 {gap['angle']:+.1f}°, 폭 {gap['width']:.0f}px):")
            print(f"  음향: {audio_score:.2f} × {weights['audio']:.0%} = {audio_score * weights['audio']:.2f}")
            print(f"  틈:   {gap_score:.2f} × {weights['gap']:.0%} = {gap_score * weights['gap']:.2f}")
            print(f"  → 최종: {total_score:.2f}")

        # === 3. 최고 점수 선택 ===
        gap_scores.sort(key=lambda x: x['total_score'], reverse=True)
        best = gap_scores[0]

        print(f"\n✅ 최종 선택: 틈 #{gaps.index(best['gap'])} (점수 {best['total_score']:.2f}))")

        return {
            'best_gap': best['gap'],
            'mode': mode,
            'score': best['total_score'],
            'all_scores': gap_scores
        }
