import 'package:flutter/material.dart';
import 'screens/splash_screen.dart';
import 'screens/welcome_screen.dart';
import 'screens/home_screen.dart';
import 'screens/form_personal_screen.dart';
import 'screens/form_about_screen.dart';
import 'screens/form_values_screen.dart';
import 'screens/form_role_screen.dart';
import 'models/profile_database.dart';

void main() {
  runApp(const CivisApp());
}

class CivisApp extends StatelessWidget {
  const CivisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CIVIS',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => const SplashScreen(),
        '/welcome': (context) => const WelcomeScreen(),
        '/home': (context) => const HomeScreen(),
        '/form/personal': (context) => const FormPersonalScreen(),
        '/form/about': (context) => const FormAboutScreen(),
        '/form/values': (context) => const FormValuesScreen(),
        '/form/role': (context) => const FormRoleScreen(),
      },
    );
  }
}
