import 'package:flutter/material.dart';
import 'form_about_screen.dart';

class FormPersonalScreen extends StatefulWidget {
  const FormPersonalScreen({super.key});

  @override
  State<FormPersonalScreen> createState() => _FormPersonalScreenState();
}

class _FormPersonalScreenState extends State<FormPersonalScreen> {
  final _nameController = TextEditingController();
  final _telegramController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Анкета'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Индикатор прогресса
              Row(
                children: [
                  Expanded(
                    child: LinearProgressIndicator(
                      value: 0.25,
                      backgroundColor: Colors.grey.shade300,
                      valueColor: const AlwaysStoppedAnimation<Color>(Colors.blue),
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text('25%', style: TextStyle(fontSize: 12)),
                ],
              ),
              const SizedBox(height: 24),
              const Text(
                'Шаг 1 из 4',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Личная информация',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Имя',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (value) =>
                    value == null || value.isEmpty ? 'Введите имя' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _telegramController,
                decoration: const InputDecoration(
                  labelText: 'Telegram @username',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.send),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Введите Telegram';
                  }
                  if (!value.startsWith('@')) {
                    return 'Должно начинаться с @';
                  }
                  return null;
                },
              ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    if (_formKey.currentState!.validate()) {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => FormAboutScreen(
                            name: _nameController.text,
                            telegram: _telegramController.text,
                          ),
                        ),
                      );
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 56),
                  ),
                  child: const Text('Далее →', style: TextStyle(fontSize: 18)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
