import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { theme } from '../../config/theme';

interface Props {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'danger' | 'warning' | 'secondary';
  loading?: boolean;
  disabled?: boolean;
}

export const HighContrastButton: React.FC<Props> = ({
  title,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
}) => {
  const getColors = () => {
    switch (variant) {
      case 'danger':
        return { bg: theme.colors.risk.CRITICAL.border, border: theme.colors.risk.CRITICAL.hex, text: theme.colors.neutral.textHeading };
      case 'warning':
        return { bg: theme.colors.risk.MODERATE.border, border: theme.colors.risk.MODERATE.hex, text: theme.colors.neutral.textHeading };
      case 'secondary':
        return { bg: theme.colors.neutral.bgElevated, border: theme.colors.neutral.borderSubtle, text: theme.colors.neutral.textBody };
      default:
        return { bg: theme.colors.brand.primary, border: theme.colors.brand.primaryHover, text: theme.colors.neutral.textHeading };
    }
  };

  const colors = getColors();

  return (
    <TouchableOpacity
      activeOpacity={0.8}
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        styles.button,
        { backgroundColor: colors.bg, borderColor: colors.border },
        (disabled || loading) && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={colors.text} size="small" />
      ) : (
        <Text style={[styles.text, { color: colors.text }]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    minHeight: 48,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: theme.spacing.spacious.radius,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 6,
  },
  text: {
    fontSize: theme.typography.sizes.cardTitle,
    fontWeight: '800',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    fontFamily: theme.typography.fontPrimary,
  },
  disabled: {
    opacity: 0.5,
  },
});
