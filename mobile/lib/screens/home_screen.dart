import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../services/storage_service.dart';
import '../models/molecule.dart';
import '../widgets/molecule_card.dart';
import '../widgets/loading_indicator.dart';
import '../utils/constants.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 0;
  List<Molecule> _history = [];
  bool _loadingHistory = true;

  final _storage = StorageService();

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    final history = await _storage.getHistory();
    setState(() {
      _history = history;
      _loadingHistory = false;
    });
  }

  void _onItemTapped(int index) {
    setState(() => _selectedIndex = index);
    switch (index) {
      case 1:
        context.go(Constants.routeBatch);
        break;
      case 2:
        context.go(Constants.routeJobs);
        break;
      case 3:
        context.go(Constants.routeSettings);
        break;
    }
  }

  void _navigateToCompute() => context.go(Constants.routeCompute);
  void _navigateToBatch() => context.go(Constants.routeBatch);
  void _navigateToJobs() => context.go(Constants.routeJobs);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Q-Mol'),
        actions: [
          authState.when(
            data: (state) => state == AuthState.authenticated
                ? Chip(
                    label: const Text('FREE'),
                    backgroundColor: Constants.qmolAccent.withAlpha(40),
                    labelStyle: TextStyle(
                      color: Constants.qmolAccent,
                      fontWeight: FontWeight.bold,
                    ),
                  )
                : const SizedBox.shrink(),
            loading: () => const SizedBox(width: 40, child: LoadingIndicator(size: 16)),
            error: (_, __) => const SizedBox.shrink(),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadHistory,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Card(
                  elevation: 2,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Quota', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        LinearProgressIndicator(
                          value: 0.1,
                          backgroundColor: theme.colorScheme.surfaceContainerHighest,
                          valueColor: AlwaysStoppedAnimation<Color>(Constants.qmolAccent),
                          minHeight: 8,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '50 / 500 used this month',
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text('Quick Actions', style: theme.textTheme.titleMedium),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    _ActionButton(
                      icon: Icons.calculate,
                      label: 'New Computation',
                      onTap: _navigateToCompute,
                    ),
                    _ActionButton(
                      icon: Icons.upload_file,
                      label: 'Upload CSV',
                      onTap: _navigateToBatch,
                    ),
                    _ActionButton(
                      icon: Icons.work_history,
                      label: 'View Jobs',
                      onTap: _navigateToJobs,
                    ),
                  ],
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Recent History', style: theme.textTheme.titleMedium),
                    TextButton(
                      onPressed: () => context.go(Constants.routeCompute),
                      child: const Text('See all'),
                    ),
                  ],
                ),
              ),
            ),
            if (_loadingHistory)
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: LoadingIndicator(message: 'Loading history...'),
                ),
              )
            else if (_history.isEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    children: [
                      Icon(Icons.history, size: 48, color: theme.colorScheme.onSurface.withAlpha(100)),
                      const SizedBox(height: 8),
                      Text(
                        'No recent computations',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              )
            else
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final mol = _history[index];
                    return MoleculeCard(
                      molecule: mol,
                      onTap: () => context.go('/molecule/${Uri.encodeComponent(mol.smiles)}'),
                    );
                  },
                  childCount: _history.length > 10 ? 10 : _history.length,
                ),
              ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.calculate), label: 'Compute'),
          BottomNavigationBarItem(icon: Icon(Icons.batch_prediction), label: 'Batch'),
          BottomNavigationBarItem(icon: Icon(Icons.work_history), label: 'Jobs'),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 20),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}
