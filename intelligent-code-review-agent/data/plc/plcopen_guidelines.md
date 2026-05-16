# PLCopen Coding Guidelines

## Naming Conventions

### Variables
- Use descriptive names: `MotorSpeed` not `MS`
- Prefix I/O variables: `i_StartButton`, `o_MotorRunning`
- Prefix internal variables: `int_Counter`, `b_Flag`
- Use camelCase for local variables
- Use UPPER_CASE for constants

### Function Blocks
- Use PascalCase: `MotorController`, `TemperatureMonitor`
- Name should describe the function: `ConveyorControl` not `FB1`

## Program Structure

### Variable Declarations
- Group variables by scope (VAR_INPUT, VAR_OUTPUT, VAR, VAR_IN_OUT)
- Initialize all variables with default values
- Add comments for non-obvious variables

### Code Organization
- One function block per logical operation
- Keep function blocks under 200 lines
- Use structured text (ST) for complex logic
- Use ladder diagram (LD) for simple interlocks

## Safety

### Watchdog Timers
- Always use watchdog timers for safety-critical operations
- Implement timeout detection for communications
- Monitor cycle time violations

### Interlocks
- Implement mechanical interlocks in software as backup
- Use positive logic (TRUE = safe) for safety signals
- Implement emergency stop logic in every program

### Bounds Checking
- Check array indices before access
- Validate sensor readings against physical limits
- Implement rate-of-change limits for actuators

## Communication

### Error Handling
- Implement communication timeout detection
- Use heartbeat signals for connection monitoring
- Handle communication loss gracefully

### Data Validation
- Validate received data before use
- Implement CRC or checksum verification
- Use sequence numbers for message ordering

## Documentation

### Inline Comments
- Comment all I/O mappings
- Document safety-critical logic
- Explain non-obvious calculations

### Function Block Documentation
- Describe the purpose and behavior
- List all inputs and outputs
- Document timing requirements
- Note safety considerations
