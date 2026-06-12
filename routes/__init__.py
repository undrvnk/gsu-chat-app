def register_routes(app):
    from routes import admin, api, faculty, profile, programs, public, student

    public.register(app)
    profile.register(app)
    programs.register(app)
    student.register(app)
    faculty.register(app)
    admin.register(app)
    api.register(app)
