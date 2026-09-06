import 'package:flutter/material.dart';
import 'form_role_screen.dart';

class FormValuesScreen extends StatefulWidget {
  final String name;
  final String telegram;
  final String text;

  const FormValuesScreen({
    super.key,
    required this.name,
    required this.telegram,
    required this.text,
  });

  @override
  State<FormValuesScreen> createState() => _FormValuesScreenState();
}

class _FormValuesScreenState extends State<FormValuesScreen> {
  final List<String> _allValues = [
    'Честность',
    'Экспертиза',
    'Инициатива',
    'Надёжность',
    'Скорость',
    'Эмпатия',
    'Системность',
    'Креативность',
    'Открытость',
    'Амбициозность',
  ];

  final List<String> _selectedValues = [];

  void _toggleValue(String value) {
    setState(() {
      if (_selectedValues.contains(value)) {
        _selectedValues.remove(value);
      } else if (_selectedValues.length < 3) {
        _selectedValues.add(value);
      }
    });
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
                    value: 0.75,
                    backgroundColor: Colors.grey.shade300,
                    valueColor: const AlwaysStoppedAnimation<Color>(Colors.blue),
                  ),
                ),
                const SizedBox(width: 8),
                const Text('75%', style: TextStyle(fontSize: 12)),
              ],
            ),
            const SizedBox(height: 24),
            const Text(
              'Шаг 3 из 4',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Ценности',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выбери 3 ключевые ценности, которые ты разделяешь в работе',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Выбрано: ${_selectedValues.length} / 3',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _allValues.map((value) {
                final isSelected = _selectedValues.contains(value);
                return FilterChip(
                  label: Text(value),
                  selected: isSelected,
                  onSelected: (_) => _toggleValue(value),
                  selectedColor: Colors.blue.shade100,
                  checkmarkColor: Colors.blue,
                );
              }).toList(),
            ),
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _selectedValues.length == 3
                    ? () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => FormRoleScreen(
                              name: widget.name,
                              telegram: widget.telegram,
                              text: widget.text,
                              values: _selectedValues.join(', '),
                            ),
                          ),
                        );
                      }
                    : null,
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 56),
                ),
                child: const Text('Далее →', style: TextStyle(fontSize: 18)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
