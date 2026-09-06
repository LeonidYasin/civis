import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../models/profile.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final Dio _dio = Dio();

  Future<bool> submitProfile(Profile profile) async {
    try {
      final apiUrl = dotenv.env['API_URL'];
      if (apiUrl == null) {
        print('API_URL не задан в .env');
        return false;
      }

      final response = await _dio.post(
        '$apiUrl/submit',
        data: profile.toMap(),
      );

      return response.statusCode == 200;
    } catch (e) {
      print('Ошибка отправки: $e');
      return false;
    }
  }
}
