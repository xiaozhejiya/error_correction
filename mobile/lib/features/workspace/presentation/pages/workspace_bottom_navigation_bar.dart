import 'package:flutter/material.dart';

class WorkspaceBottomNavigationBar extends StatelessWidget {
  const WorkspaceBottomNavigationBar({
    required this.selectedIndex,
    required this.onDestinationSelected,
    super.key,
  });

  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  @override
  Widget build(BuildContext context) {
    return NavigationBar(
      selectedIndex: selectedIndex,
      onDestinationSelected: onDestinationSelected,
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.auto_awesome_rounded),
          label: '智能录入',
        ),
        NavigationDestination(
          icon: Icon(Icons.collections_bookmark_rounded),
          label: '库',
        ),
        NavigationDestination(
          icon: Icon(Icons.lightbulb_outline_rounded),
          label: '台灯',
        ),
        NavigationDestination(
          icon: Icon(Icons.chat_bubble_outline_rounded),
          label: '对话',
        ),
        NavigationDestination(
          icon: Icon(Icons.person_outline_rounded),
          label: '我的',
        ),
      ],
    );
  }
}
