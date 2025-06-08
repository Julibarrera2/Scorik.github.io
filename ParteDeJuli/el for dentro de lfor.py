# Un for que analiza cada tramo de 10 segundos
notas_json = []
if pitch_data:
    segmento_duracion = 10.0  # duración de cada tramo en segundos
    total_tiempo = pitch_data[-1][0]
    num_segmentos = int(np.ceil(total_tiempo / segmento_duracion))
    print("Total tiempo del audio recortado:", duracion_audio_trim, "segundos")
    print("Segmento duración:", segmento_duracion)
    print("Número de segmentos:", num_segmentos)
    for s in range(num_segmentos):
        inicio_seg = s * segmento_duracion
        fin_seg = (s + 1) * segmento_duracion
        print(f"\n🔍 Analizando tramo {s+1}/{num_segmentos} ({inicio_seg:.2f}s - {fin_seg:.2f}s)")
        # Filtramos solo los pitches de este tramo
        segmento = [p for p in pitch_data if inicio_seg <= p[0] < fin_seg]
        if not segmento:
            print("  ⚠️ Sin datos en este tramo.")
            continue
        # Si es el último tramo, suavizamos frecuencias con media móvil (ventana 3)
        if s == num_segmentos - 1 and len(segmento) >= 3:
            tiempos_seg = [p[0] for p in segmento]
            freqs_seg = [p[1] for p in segmento]
            freqs_suavizadas = np.convolve(freqs_seg, np.ones(3)/3, mode='same')
            segmento = list(zip(tiempos_seg, freqs_suavizadas))
        # Inicializamos variables de agrupamiento
        inicio = segmento[0][0]
        freq_actual = segmento[0][1]
        nota_actual = frecuencia_a_nota(freq_actual)
        for i in range(1, len(segmento)):
            t, f = segmento[i]
            #Antes de la condición, mostramos la diferencia en semitonos
            diferencia_en_semitonos = semitonos(f, freq_actual)
            print(f"comparando freq_actual={freq_actual:.1f}Hz y f={f:.1f}Hz ⇒ Δ={diferencia_en_semitonos:.3f} semitonos")
            # Si la nota nueva es diferente (por semitonos), se cierra la nota anterior
            # Si la nota nueva es suficientemente distinta, cerramos la nota anterior
            if diferencia_en_semitonos > NOTA_UMBRAL_VARIACION:
                duracion = t - inicio
                #print(f"    → Duración calculada: {duracion:.3f}s")
                if duracion >= MIN_DURACION_NOTA:
                    figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                    notas_json.append({
                        "nota": nota_actual,
                        "inicio": round(inicio, 3),
                        "duracion": round(duracion, 3),
                        "compas": compas,
                        "figura": figura,
                        "tempo": int(tempo)
                    })
                # Se actualiza a la nueva nota
                inicio = t
                freq_actual = f
                nota_actual = frecuencia_a_nota(f)
            # Advertencia si hay separación anormal (solo en último tramo)
            if s == num_segmentos - 1 and abs(t - inicio) > 2.0:
                print(f"  ⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
        # Cierre de la última nota del tramo
        duracion = segmento[-1][0] - inicio
        if MIN_DURACION_NOTA <= duracion < 6.0:
            figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
            notas_json.append({
                "nota": nota_actual,
                "inicio": round(inicio, 3),
                "duracion": round(duracion, 3),
                "compas": compas,
                "figura": figura,
                "tempo": int(tempo)
            })
        # Verificación extra de duración excesiva (último tramo)
        if s == num_segmentos - 1 and duracion > 6.0:
            print(f"⚠️ Nota descartada por duración excesiva: {duracion:.2f}s")

            # Si hay silencio significativo, se agrega pausa
            if t - inicio > 1.5:  # más de 1.5 segundos sin notas válidas
                print(f"Silencio detectado entre {inicio:.2f}s y {t:.2f}s")

            if abs(pitch_data[i][0] - inicio) > 0.03:   
                if abs(t - inicio) > 2.0:
                    print(f"⚠️ Agrupamiento raro detectado entre {inicio:.2f}s y {t:.2f}s")
                duracion = max(t - inicio, 0)
                if duracion == 0:
                    continue
                if duracion > 6.0:
                    print(f"⚠️ Nota descartada por duración demasiado larga: {duracion:.2f}s")
                    continue
                if duracion > 0.02:  # descartar eventos muy breves
                    figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
                    notas_json.append({
                        "nota": nota_actual,
                        "inicio": round(inicio, 3),
                        "duracion": round(max(duracion, 0.03), 3),
                        "compas": compas,
                        "figura": figura,
                        "tempo": int(tempo)
                    })
                inicio = t

        # Agregar la última nota que se estaba tocando al final del audio
        duracion = pitch_data[-1][0] - inicio
        if 0.02 < duracion < 5:  # límite máximo de duración razonable
            figura, compas = calcular_figura_y_compas(duracion, tempo, inicio)
            notas_json.append({
                "nota": nota_actual,
                "inicio": round(inicio, 3),
                "duracion": round(max(duracion, 0.03), 3),
                "compas": compas,
                "figura": figura,
                "tempo": int(tempo)
                })
        if notas_json and notas_json[-1]["duracion"] < 0.05:
            print(f"⚠️ Nota final descartada por ser demasiado corta: {notas_json[-1]['duracion']}s")
            notas_json = notas_json[:-1]