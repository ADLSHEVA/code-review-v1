# Python Coding Guidelines

## Security

### Input Validation
- Always validate and sanitize user input before processing
- Use parameterized queries for database operations — never use string formatting
- Validate file paths to prevent path traversal attacks

### Authentication & Passwords
- NEVER store passwords in plain text — always hash with bcrypt or argon2
- Use secrets.compare_digest() for timing-safe string comparison
- Implement rate limiting on authentication endpoints

### Secrets Management
- NEVER hardcode API keys, passwords, or tokens in source code
- Use environment variables or a secrets manager
- Rotate secrets regularly

## Error Handling

### Exception Best Practices
- Catch specific exceptions, never use bare `except:`
- Log exceptions with sufficient context for debugging
- Use custom exception classes for domain-specific errors
- Clean up resources in finally blocks or use context managers

## Code Quality

### Naming Conventions
- Functions and variables: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Private members: prefix with underscore (_private_method)

### Type Hints
- All public functions must have complete type hints
- Use Optional[X] for nullable parameters
- Use Union[X, Y] for multiple possible types (Python < 3.10)

### Documentation
- All public classes and functions must have docstrings
- Use Google-style docstring format
- Include Args, Returns, and Raises sections

## Performance

### Database
- Use connection pooling for database connections
- Avoid N+1 query patterns — use joins or batch queries
- Add indexes for frequently queried columns

### General
- Use generators for large datasets to reduce memory usage
- Cache expensive computations when appropriate
- Profile before optimizing — don't guess at bottlenecks
