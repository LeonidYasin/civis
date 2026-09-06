class Profile {
  final int? id;
  final String name;
  final String text;
  final String values;
  final String role;
  final String telegram;
  final String createdAt;

  Profile({
    this.id,
    required this.name,
    required this.text,
    required this.values,
    required this.role,
    required this.telegram,
    required this.createdAt,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'name': name,
      'text': text,
      'values': values,
      'role': role,
      'telegram': telegram,
      'created_at': createdAt,
    };
  }

  factory Profile.fromMap(Map<String, dynamic> map) {
    return Profile(
      id: map['id'],
      name: map['name'],
      text: map['text'],
      values: map['values'],
      role: map['role'],
      telegram: map['telegram'],
      createdAt: map['created_at'],
    );
  }
}
