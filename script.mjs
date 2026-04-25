import fs from 'fs';
import Fuse from 'fuse.js';

// 1. Diccionario de Amenazas (Términos normalizados y su "peso" de riesgo)
const diccionarioAmenazas = [
    { termino: "cjng", peso: 50 },
    { termino: "cartel", peso: 50 },
    { termino: "4L", peso: 40 },
    { termino: "reclutamiento", peso: 50 },
    { termino: "empresa", peso: 20 }, // Puede ser normal, peso medio
    { termino: "belico", peso: 30 },
    { termino: "alucin", peso: 15 },
    { termino: "plaza", peso: 20 },
    { termino: "sinaloa", peso: 10 }
];

// 2. Diccionario de Atenuantes (Palabras que indican que el video es seguro/comida)
const palabrasSeguras = ["pizza", "food", "chicken", "recipe", "comida", "pollo", "cheese", "asmr"];

// 3. Configuración de Fuse.js para Búsqueda Difusa (Tolerancia a errores ortográficos)
const fuseOptions = {
    keys: ['termino'],
    includeScore: true,
    threshold: 0.3, // 0.0 es coincidencia exacta. 0.3 permite errores (ej. "reclutamiendo" vs "reclutamiento")
};

const fuse = new Fuse(diccionarioAmenazas, fuseOptions);

// 4. Lógica de Evaluación (El corazón del Filtro Alpha)
function evaluarReel(tiktok) {
    let threatScore = 0;
    const descripcion = tiktok.text ? tiktok.text.toLowerCase() : "";
    let hashtags = [];

    if (tiktok.hashtags && Array.isArray(tiktok.hashtags)) {
        hashtags = tiktok.hashtags.map(ht => ht.name.toLowerCase());
        if (hashtags.length == 0 && descripcion == "") {
            return {
                score: 30,
                motivo: "Filtro sin capacidades suficientes de identificación",
                url: tiktok.webVideoUrl
            };
        }
    }

    // Unir todo el texto analizable (Descripción + Hashtags)
    const textoCompleto = descripcion + " " + hashtags.join(" ");

    // A) REGLA DE DESCARTE RÁPIDO (La regla de la Pizza/Comida)
    // Si contiene emojis de riesgo pero también palabras de comida, penalizamos el score.
    const tieneEmojiRiesgo = textoCompleto.includes('🍕') || textoCompleto.includes('🐓') || textoCompleto.includes('🥷');
    const esContextoComida = palabrasSeguras.some(palabra => textoCompleto.includes(palabra));

    if (esContextoComida) {
        return { score: 0, motivo: "Falso Positivo detectado (Contexto de comida)", url: tiktok.webVideoUrl };
    }

    // B) ANÁLISIS DE AMENAZAS CON FUSE.JS
    // Separamos el texto en palabras para analizarlas
    const palabrasEnTexto = textoCompleto.split(/[\s,]+/);
    const hallazgos = new Set(); // Para no sumar la misma palabra dos veces

    palabrasEnTexto.forEach(palabra => {
        // Fuse busca si la palabra del reel se parece a alguna de nuestro diccionario
        const resultados = fuse.search(palabra);

        if (resultados.length > 0) {
            // Tomamos la mejor coincidencia
            const mejorCoincidencia = resultados[0].item;

            if (!hallazgos.has(mejorCoincidencia.termino)) {
                threatScore += mejorCoincidencia.peso;
                hallazgos.add(mejorCoincidencia.termino);
            }
        }
    });

    // C) PUNTUACIÓN DIRECTA POR EMOJIS (Fuera del contexto de comida)
    if (textoCompleto.includes('🍕') && textoCompleto.includes('🐓')) threatScore += 40; // Combinación de facciones
    else if (textoCompleto.includes('🍕') || textoCompleto.includes('🥷')) threatScore += 15;
    if (textoCompleto.includes('🪖')) threatScore += 20;

    return {
        score: threatScore,
        motivo: `Puntos sumados por: [${Array.from(hallazgos).join(', ')}] y análisis de emojis.`,
        url: tiktok.webVideoUrl
    };
}

// 5. Función Principal
function ejecutarFiltroAlpha() {
    try {
        const dataRaw = fs.readFileSync('./scrapetest.json', 'utf-8');
        const tiktoks = JSON.parse(dataRaw);

        console.log(`\n🛡️ INICIANDO FILTRO ALPHA (Threat Scoring) - ${tiktoks.length} publicaciones.\n`);

        let threatsNumber = 0;
        tiktoks.forEach((tiktok, index) => {
            const evaluacion = evaluarReel(tiktok);

            // Solo imprimimos los que superen un umbral de sospecha (ej. más de 20 puntos)
            // o imprimimos todo para depurar
            console.log(`[Reel #${index + 1}] | ID: ${tiktok.id}`);
            console.log(`📝 Texto: ${tiktok.text ? tiktok.text.substring(0, 50) + "..." : "N/A"}`);

            if (evaluacion.score >= 30) {
                console.log(`🔴 PELIGRO ALTO | Score: ${evaluacion.score}`);
                ++threatsNumber;
            } else if (evaluacion.score > 0) {
                console.log(`🟡 SOSPECHOSO | Score: ${evaluacion.score}`);
            } else {
                console.log(`🟢 SEGURO | Score: 0`);
            }
            console.log(`Link al video: ${evaluacion.url}`);

            console.log(`🔍 Detalle: ${evaluacion.motivo}`);
            console.log('--------------------------------------------------');
        });

        console.log(`Threats found: ${threatsNumber}/${tiktoks.length}`);

    } catch (error) {
        console.error("🚨 Error al procesar:", error.message);
    }
}

ejecutarFiltroAlpha();