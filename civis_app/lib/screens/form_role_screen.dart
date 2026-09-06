import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/profile.dart';
import '../models/profile_database.dart';

class FormRoleScreen extends StatefulWidget {
  const FormRoleScreen({super.key});

  @override
  State<FormRoleScreen> createState() => _FormRoleScreenState();
}

class _FormRoleScreenState extends State<FormRoleScreen> {
  String? _selectedRole;
  final List<String> _roles = [
    'Исполнитель',
    'Заказчик',
    'Координатор',
    'Инвестор',
  ];

  final Map<String, IconData> _roleIcons = {
    'Исполнитель': Icons.build,
    'Заказчик': Icons.shopping_cart,
    'Координатор': Icons.people,
    'Инвестор': Icons.trending_up,
  };

  Future<void> _submitForm() async {
    // В реальном приложении данные нужно передавать через навигацию
    // или использовать глобальное состояние (например, Provider или BLoC)
    // Пока создадим фиктивный профиль для демонстрации
    final profile = Profile(
      name: 'Тестовый пользователь',
      text: 'Текст о себе (заглушка)',
      values: 'Честность, Экспертиза, Инициатива',
      role: _selectedRole!,
      telegram: '@testuser',
      createdAt: DateTime.now().toIso8601String(),
    );

    // Сохраняем в локальную базу
    await ProfileDatabase.instance.insertProfile(profile);

    // Отмечаем, что профиль заполнен
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('has_profile', true);

    if (mounted) {
      Navigator.pushReplacementNamed(context, '/home');
    }
  }

  @override
  Widget build(BuildContext context) {
    final canProceed = _selectedRole != null;

    return Scaffold(
      appBar: AppBar(title: const Text('Шаг 4 из 4 — Роль')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const LinearProgressIndicator(value: 1.0),
            const SizedBox(height: 24),
            const Text(
              'Твоя основная роль сейчас?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),
            Expanded(
              child: ListView.separated(
                itemCount: _roles.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final role = _roles[index];
                  final isSelected = _selectedRole == role;
                  return Card(
                    elevation: isSelected ? 4 : 1,
                    color: isSelected ? Colors.blue.shade50 : Colors.white,
                    child: ListTile(
                      leading: Icon(
                        _roleIcons[role],
                        color: isSelected ? Colors.blue : Colors.grey,
                        size: 32,
                      ),
                      title: Text(
                        role,
                        style: TextStyle(
                          fontWeight:
                              isSelected ? FontWeight.bold : FontWeight.normal,
                          color: isSelected ? Colors.blue : Colors.black,
                        ),
                      ),
                      trailing: isSelected
                          ? const Icon(Icons.check_circle, color: Colors.blue)
                          : null,
                      onTap: () {
                        setState(() {
                          _selectedRole = role;
                        });
                      },
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: canProceed ? _submitForm : null,
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 56),
                backgroundColor: canProceed ? Colors.blue : Colors.grey,
              ),
              child: Text(
                canProceed ? 'Стать гражданином Civis' : 'Выберите роль',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
