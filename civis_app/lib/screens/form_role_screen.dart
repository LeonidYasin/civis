import 'package:flutter/material.dart';
import '../models/profile.dart';
import '../models/profile_database.dart';
import '../services/api_service.dart';
import 'home_screen.dart';

class FormRoleScreen extends StatefulWidget {
  final String name;
  final String telegram;
  final String text;
  final String values;

  const FormRoleScreen({
    super.key,
    required this.name,
    required this.telegram,
    required this.text,
    required this.values,
  });

  @override
  State<FormRoleScreen> createState() => _FormRoleScreenState();
}

class _FormRoleScreenState extends State<FormRoleScreen> {
  String _selectedRole = 'Исполнитель';
  bool _isSubmitting = false;

  final List<String> _roles = [
    'Исполнитель',
    'Заказчик',
    'Координатор',
    'Инвестор',
  ];

  final Map<String, IconData> _roleIcons = {
    'Исполнитель': Icons.construction,
    'Заказчик': Icons.shopping_cart,
    'Координатор': Icons.people,
    'Инвестор': Icons.trending_up,
  };

  Future<void> _submitForm() async {
    setState(() => _isSubmitting = true);

    final profile = Profile(
      name: widget.name,
      text: widget.text,
      values: widget.values,
      role: _selectedRole,
      telegram: widget.telegram,
      createdAt: DateTime.now().toIso8601String(),
    );

    // Сохраняем локально
    final id = await ProfileDatabase.instance.insertProfile(profile);
    print('Сохранено в базу с id: $id');

    // Отправляем на сервер
    final apiService = ApiService();
    final sent = await apiService.submitProfile(profile);

    if (!mounted) return;

    setState(() => _isSubmitting = false);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          sent ? '✅ Заявка отправлена!' : '⚠️ Заявка сохранена локально',
        ),
        duration: const Duration(seconds: 2),
      ),
    );

    // Переходим на главный экран
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const HomeScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Анкета'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Индикатор прогресса
            Row(
              children: [
                Expanded(
                  child: LinearProgressIndicator(
                    value: 1.0,
                    backgroundColor: Colors.grey.shade300,
                    valueColor: const AlwaysStoppedAnimation<Color>(Colors.green),
                  ),
                ),
                const SizedBox(width: 8),
                const Text('100%', style: TextStyle(fontSize: 12)),
              ],
            ),
            const SizedBox(height: 24),
            const Text(
              'Шаг 4 из 4',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Твоя роль',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выбери основную роль в сообществе',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 24),
            ..._roles.map((role) => Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  color: _selectedRole == role ? Colors.blue.shade50 : null,
                  child: ListTile(
                    leading: Icon(
                      _roleIcons[role],
                      color: _selectedRole == role ? Colors.blue : Colors.grey,
                    ),
                    title: Text(role),
                    trailing: _selectedRole == role
                        ? const Icon(Icons.check_circle, color: Colors.blue)
                        : null,
                    onTap: () => setState(() => _selectedRole = role),
                  ),
                )),
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isSubmitting ? null : _submitForm,
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 56),
                  backgroundColor: Colors.green,
                ),
                child: _isSubmitting
                    ? const SizedBox(
                        height: 24,
                        width: 24,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Text(
                        'Стать гражданином Civis',
                        style: TextStyle(fontSize: 18),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
