import 'package:flutter/material.dart';
import 'form_values_screen.dart';

class FormAboutScreen extends StatefulWidget {
  final String name;
  final String telegram;

  const FormAboutScreen({super.key, required this.name, required this.telegram});

  @override
  State<FormAboutScreen> createState() => _FormAboutScreenState();
}

class _FormAboutScreenState extends State<FormAboutScreen> {
  final _textController = TextEditingController();
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
                      value: 0.50,
                      backgroundColor: Colors.grey.shade300,
                      valueColor: const AlwaysStoppedAnimation<Color>(Colors.blue),
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text('50%', style: TextStyle(fontSize: 12)),
                ],
              ),
              const SizedBox(height: 24),
              const Text(
                'Шаг 2 из 4',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'О себе',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Расскажи о своей суперсиле и целях',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _textController,
                maxLines: 8,
                decoration: InputDecoration(
                  labelText: 'Рассказ о себе',
                  border: const OutlineInputBorder(),
                  helperText: 'Минимум 300 символов',
                  counterText: '${_textController.text.length}/300',
                ),
                validator: (value) {
                  if (value == null || value.length < 300) {
                    return 'Текст должен быть не менее 300 символов';
                  }
                  return null;
                },
                onChanged: (value) => setState(() {}),
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
                          builder: (_) => FormValuesScreen(
                            name: widget.name,
                            telegram: widget.telegram,
                            text: _textController.text,
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
