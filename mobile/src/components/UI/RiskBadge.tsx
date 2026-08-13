import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme, MobileRiskBucketKey } from '../../config/theme';
import { getRiskCategory, evaluateMultiHorizonRisk } from '../../config/constants';

interface Props {
  score?: number;
  category?: MobileRiskBucketKey | string;
  size?: 'small' | 'medium' | 'large';
  showScore?: boolean;
  r2m?: number;
  r5m?: number;
  r10m?: number;
}

export const RiskBadge: React.FC<Props> = ({
  score,
  category,
  size = 'medium',
  showScore = true,
  r2m,
  r5m,
  r10m,
}) => {
  let catKey: MobileRiskBucketKey = 'LOW';
  let displayLabel = 'LOW';
  let numericScore = score;

  if (score !== undefined && (r2m !== undefined || r5m !== undefined || r10m !== undefined)) {
    const mhEval = evaluateMultiHorizonRisk(score, r2m, r5m, r10m);
    catKey = (mhEval.currentCategory.key as MobileRiskBucketKey) || 'LOW';
    displayLabel = mhEval.displayLabel;
  } else if (category) {
    const upper = category.toUpperCase();
    if (upper in theme.colors.risk) {
      catKey = upper as MobileRiskBucketKey;
    } else if (upper === 'SAFE') {
      catKey = 'LOW';
    }
    displayLabel = catKey;
  } else if (score !== undefined) {
    const catObj = getRiskCategory(score);
    catKey = (catObj.key as MobileRiskBucketKey) || 'LOW';
    displayLabel = catKey;
  }

  const riskToken = theme.colors.risk[catKey] || theme.colors.risk.LOW;

  const shapeSymbols: Record<MobileRiskBucketKey, string> = {
    LOW: '●',
    MODERATE: '▲',
    HIGH: '◆',
    CRITICAL: '🛑',
  };

  const isLarge = size === 'large';
  const isSmall = size === 'small';

  const fontSize = isLarge
    ? theme.typography.sizes.cardTitle
    : isSmall
    ? theme.typography.sizes.caption
    : theme.typography.sizes.body;

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: riskToken.bg,
          borderColor: riskToken.border,
          paddingHorizontal: isLarge ? 14 : isSmall ? 8 : 10,
          paddingVertical: isLarge ? 6 : isSmall ? 3 : 4,
        },
      ]}
    >
      <Text style={[styles.shape, { color: riskToken.hex, fontSize: fontSize - 2 }]}>
        {shapeSymbols[catKey]}
      </Text>
      <Text style={[styles.text, { color: riskToken.hex, fontSize }]}>
        {displayLabel}
      </Text>
      {showScore && numericScore !== undefined && r2m === undefined && (
        <Text style={[styles.scoreText, { color: riskToken.hex, fontSize }]}>
          {numericScore.toFixed(0)}%
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 1.5,
    alignSelf: 'flex-start',
    gap: 6,
  },
  shape: {
    fontWeight: '900',
  },
  text: {
    fontWeight: '800',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontFamily: theme.typography.fontPrimary,
  },
  scoreText: {
    fontWeight: '700',
    fontFamily: theme.typography.fontMono,
    borderLeftWidth: 1,
    borderLeftColor: 'rgba(255,255,255,0.2)',
    paddingLeft: 6,
    marginLeft: 2,
  },
});
