import 'package:flutter/material.dart';

class FormAboutScreen extends StatefulWidget {
  const FormAboutScreen({super.key});

  @override
  State<FormAboutScreen> createState() => _FormAboutScreenState();
}

class _FormAboutScreenState extends State<FormAboutScreen> {
  final _textController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  static const int _minLength = 300;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Шаг 2 из 4 — О себе')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const LinearProgressIndicator(value: 0.5),
              const SizedBox(height: 24),
              const Text(
                'Расскажи о своей суперсиле и целях',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Минимум 300 символов',
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: TextFormField(
                  controller: _textController,
                  maxLines: 12,
                  decoration: const InputDecoration(
                    hintText: 'Расскажи о своём опыте, навыках и целях...',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.length < _minLength) {
                      return 'Пожалуйста, напишите не менее 300 символов (сейчас ${value?.length ?? 0})';
                    }
                    return null;
                  },
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  if (_formKey.currentState!.validate()) {
                    Navigator.pushNamed(context, '/form/values');
                  }
                },
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                ),
                child: const Text('Далее →'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
