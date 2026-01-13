# fusion/adaptive_fusion.py

class AdaptiveFusion:
    """2센서 적응형 융합"""

    def __init__(self):
        self.snr_threshold = 15.0

        self.weights_audio_trust = {
            'audio': 0.70,
            'gap': 0.30
        }

        self.weights_visual_trust = {
            'audio': 0.50,
            'gap': 0.50
        }

    def fuse(self, audio_data, gaps):
        """융합 실행"""
        if not gaps or not audio_data:
            return None

        # 모드 판단
        if audio_data['snr'] >= self.snr_threshold:
            mode = "audio_trust"
            weights = self.weights_audio_trust
        else:
            mode = "visual_trust"
            weights = self.weights_visual_trust

        print(f"\n{'='*60}")
        print(f"🎯 모드: {mode}")
        print(f"   SNR: {audio_data['snr']:.1f}dB")
        print(f"   가중치: 음향 {weights['audio']:.0%} + 틈 {weights['gap']:.0%}")
        print(f"{'='*60}")

        # 점수 계산
        gap_scores = []

        for i, gap in enumerate(gaps):
            # 음향 점수
            angle_diff = abs(gap['angle'] - audio_data['angle'])
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            audio_score = max(0, 1.0 - (angle_diff / 90.0))
            snr_factor = min(1.0, max(0.5, audio_data['snr'] / 30.0))
            audio_score *= snr_factor

            # 틈 점수
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

            print(f"\n틈 #{i} (각도 {gap['angle']:+.1f}°):")
            print(f"  음향: {audio_score:.2f}")
            print(f"  틈:   {gap_score:.2f}")
            print(f"  → 최종: {total_score:.2f}")

        # 최고 점수 선택
        gap_scores.sort(key=lambda x: x['total_score'], reverse=True)
        best = gap_scores[0]

        print(f"\n✅ 선택: 틈 #{gaps.index(best['gap'])}")

        return {
            'best_gap': best['gap'],
            'mode': mode,
            'score': best['total_score'],
            'all_scores': gap_scores
        }
