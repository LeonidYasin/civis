import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'profile.dart';

class ProfileDatabase {
  static final ProfileDatabase instance = ProfileDatabase._init();
  static Database? _database;

  ProfileDatabase._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('civis.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(path, version: 1, onCreate: _createDB);
  }

  Future<void> _createDB(Database db, int version) async {
    await db.execute('''
      CREATE TABLE profiles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        text TEXT,
        values TEXT,
        role TEXT,
        telegram TEXT,
        created_at TEXT
      )
    ''');
  }

  Future<int> insertProfile(Profile profile) async {
    final db = await instance.database;
    return await db.insert('profiles', profile.toMap());
  }

  Future<List<Profile>> getAllProfiles() async {
    final db = await instance.database;
    final result = await db.query('profiles');
    return result.map((map) => Profile.fromMap(map)).toList();
  }

  Future<void> deleteProfile(int id) async {
    final db = await instance.database;
    await db.delete('profiles', where: 'id = ?', whereArgs: [id]);
  }
}
