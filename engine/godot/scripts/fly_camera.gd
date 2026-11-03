extends Camera3D
## A simple free camera to look at the streamed city (the walker comes in prompt 73).
## Right mouse button held: look around. W A S D: move, Q / E: down / up, Shift: faster.

@export var speed := 20.0
@export var fast_factor := 8.0
@export var mouse_sensitivity := 0.003

var _yaw := 0.0
var _pitch := 0.0


func _ready() -> void:
	_sync_angles()


func _sync_angles() -> void:
	_yaw = rotation.y
	_pitch = rotation.x


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		if event.pressed:
			_sync_angles()   # the streamer may have pointed the camera at the start view
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_yaw -= event.relative.x * mouse_sensitivity
		_pitch = clampf(_pitch - event.relative.y * mouse_sensitivity, -1.5, 1.5)
		rotation = Vector3(_pitch, _yaw, 0.0)


func _process(delta: float) -> void:
	var move := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):
		move.z -= 1.0
	if Input.is_physical_key_pressed(KEY_S):
		move.z += 1.0
	if Input.is_physical_key_pressed(KEY_A):
		move.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D):
		move.x += 1.0
	if Input.is_physical_key_pressed(KEY_E):
		move.y += 1.0
	if Input.is_physical_key_pressed(KEY_Q):
		move.y -= 1.0
	if move == Vector3.ZERO:
		return
	var step := speed * delta * (fast_factor if Input.is_physical_key_pressed(KEY_SHIFT) else 1.0)
	translate(move.normalized() * step)
