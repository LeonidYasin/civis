import 'package:flutter/material.dart';

class FormValuesScreen extends StatefulWidget {
  const FormValuesScreen({super.key});

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
  static const int _maxSelection = 3;

  void _toggleValue(String value) {
    setState(() {
      if (_selectedValues.contains(value)) {
        _selectedValues.remove(value);
      } else if (_selectedValues.length < _maxSelection) {
        _selectedValues.add(value);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final canProceed = _selectedValues.length == _maxSelection;

    return Scaffold(
      appBar: AppBar(title: const Text('Шаг 3 из 4 — Ценности')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const LinearProgressIndicator(value: 0.75),
            const SizedBox(height: 24),
            const Text(
              'Что для тебя важно в работе?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Выбери ровно $_maxSelection ценности (выбрано ${_selectedValues.length})',
              style: const TextStyle(fontSize: 14, color: Colors.grey),
            ),
            const SizedBox(height: 24),
            Expanded(
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _allValues.map((value) {
                  final isSelected = _selectedValues.contains(value);
                  return FilterChip(
                    label: Text(value),
                    selected: isSelected,
                    onSelected: (_) => _toggleValue(value),
                    selectedColor: Colors.blue.shade100,
                    backgroundColor: Colors.grey.shade200,
                    checkmarkColor: Colors.blue,
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: canProceed
                  ? () {
                      Navigator.pushNamed(context, '/form/role');
                    }
                  : null,
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 50),
                backgroundColor: canProceed ? Colors.blue : Colors.grey,
              ),
              child: Text(
                canProceed ? 'Далее →' : 'Выберите ещё ${_maxSelection - _selectedValues.length} ценность(ей)',
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
