import 'package:flutter/material.dart';
import '../models/job.dart';
import '../utils/constants.dart';

class JobListItem extends StatelessWidget {
  final Job job;
  final VoidCallback? onTap;
  final VoidCallback? onCancel;
  final VoidCallback? onDownload;

  const JobListItem({
    super.key,
    required this.job,
    this.onTap,
    this.onCancel,
    this.onDownload,
  });

  Color _statusColor() {
    switch (job.status.toLowerCase()) {
      case 'done':
      case 'completed':
        return Constants.qmolSuccess;
      case 'failed':
      case 'error':
        return Constants.qmolError;
      case 'running':
      case 'processing':
        return Constants.qmolWarning;
      case 'queued':
      case 'pending':
      default:
        return Colors.blue;
    }
  }

  IconData _statusIcon() {
    switch (job.status.toLowerCase()) {
      case 'done':
      case 'completed':
        return Icons.check_circle;
      case 'failed':
      case 'error':
        return Icons.error;
      case 'running':
      case 'processing':
        return Icons.hourglass_top;
      case 'queued':
      case 'pending':
      default:
        return Icons.schedule;
    }
  }

  double? _progressValue() {
    if (job.total == 0) return null;
    return (job.nProcessed / job.total).clamp(0.0, 1.0);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final statusColor = _statusColor();

    return Semantics(
      label: 'Job ${job.id}, status ${job.status}, ${job.nProcessed} of ${job.total} processed',
      child: Card(
        elevation: 2,
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(_statusIcon(), color: statusColor, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Job ${job.id.substring(0, job.id.length > 8 ? 8 : job.id.length)}...',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withAlpha(40),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        job.status.toUpperCase(),
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: statusColor,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: _progressValue(),
                  backgroundColor: theme.colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                  minHeight: 6,
                  borderRadius: BorderRadius.circular(3),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${job.nProcessed} / ${job.total} molecules',
                      style: theme.textTheme.bodySmall,
                    ),
                    Text(
                      job.createdAt ?? 'Just now',
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ),
                if (job.error != null && job.error!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Error: ${job.error}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Constants.qmolError,
                    ),
                  ),
                ],
                if (onCancel != null || onDownload != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (onCancel != null &&
                          (job.status == 'running' || job.status == 'queued' || job.status == 'processing'))
                        TextButton.icon(
                          onPressed: onCancel,
                          icon: const Icon(Icons.cancel, size: 18),
                          label: const Text('Cancel'),
                        ),
                      if (onDownload != null &&
                          (job.status == 'done' || job.status == 'completed'))
                        TextButton.icon(
                          onPressed: onDownload,
                          icon: const Icon(Icons.download, size: 18),
                          label: const Text('Download'),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
