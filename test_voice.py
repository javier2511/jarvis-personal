from voice import escuchar, hablar

print("Prueba de micrófono iniciada")
hablar("Di algo")

texto = escuchar()

print("Texto detectado:", texto)
hablar(f"Escuché: {texto}")