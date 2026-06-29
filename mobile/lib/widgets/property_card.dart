import 'package:flutter/material.dart';
import '../models/property.dart';
import '../utils/constants.dart';

class PropertyCard extends StatelessWidget {
  final Property property;
  final VoidCallback? onTap;

  const PropertyCard({super.key, required this.property, this.onTap});

  Color _statusColor() {
    switch (property.status.toLowerCase()) {
      case 'ok':
      case 'pass':
      case 'good':
        return Constants.qmolSuccess;
      case 'warning':
      case 'moderate':
        return Constants.qmolWarning;
      case 'fail':
      case 'alert':
      case 'bad':
        return Constants.qmolError;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor();
    final theme = Theme.of(context);

    return Semantics(
      label: 'Property ${property.name}, value ${property.value} ${property.unit ?? ''}',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Card(
          elevation: 2,
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        property.name,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    if (property.inDomain == false)
                      Tooltip(
                        message: 'Outside applicability domain',
                        child: Icon(
                          Icons.warning_amber,
                          color: Constants.qmolWarning,
                          size: 18,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      property.value != null
                          ? property.value!.toStringAsFixed(2)
                          : 'N/A',
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: statusColor,
                      ),
                    ),
                    if (property.unit != null) ...[
                      const SizedBox(width: 4),
                      Text(
                        property.unit!,
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value: property.confidence.clamp(0.0, 1.0),
                  backgroundColor: theme.colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation<Color>(statusColor.withAlpha(180)),
                  minHeight: 4,
                  borderRadius: BorderRadius.circular(2),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Confidence: ${(property.confidence * 100).toStringAsFixed(0)}%',
                      style: theme.textTheme.bodySmall,
                    ),
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: statusColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
