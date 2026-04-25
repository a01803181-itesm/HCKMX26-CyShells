import fs from 'fs';
import { ApifyClient } from 'apify-client';
import Fuse from 'fuse.js';
import AhoCorasick from 'aho-corasick'; // Algoritmo de alta eficiencia

// 1. Configuración de Clientes y Diccionarios
const apifyClient = new ApifyClient({
    token: process.env.API_TOKEN, // Pon tu token real
});

const diccionarioAmenazas = [
    { termino: "cjng", peso: 50 },
    { termino: "cartel", peso: 50 },
    { termino: "4L", peso: 40 },
    { termino: "reclutamiento", peso: 50 },
    { termino: "belico", peso: 30 },
    { termino: "alucin", peso: 15 },
    { termino: "plaza", peso: 20 },
    { termino: "sinaloa", peso: 10 }
];

const palabrasSeguras = ["pizza", "food", "recipe", "comida", "pollo", "chef"];

// 2. Configuración de Filtro Beta (Aho-Corasick)
const frasesReclutamiento = ["info", "cuanto pagan", "manda dm", "quiero trabajar", "jalo", "me interesa", "donde firmo"];
const frasesAdmiracion = ["puro cjng", "arriba las 4l", "al millon", "señor de los gallos", "la empresa", "puro jefe"];

const acReclutamiento = new AhoCorasick(frasesReclutamiento);
const acAdmiracion = new AhoCorasick(frasesAdmiracion);

// 3. Lógica del Filtro Alpha (Fuse.js)
const fuse = new Fuse(diccionarioAmenazas, { keys: ['termino'], threshold: 0.3 });

function evaluarReelAlpha(tiktok) {
    const texto = (tiktok.text || "").toLowerCase();
    const hashtags = (tiktok.hashtags || []).map(h => h.name.toLowerCase()).join(" ");
    const todoElTexto = texto + " " + hashtags;

    // Regla de descarte de comida
    if ((todoElTexto.includes('🍕') || todoElTexto.includes('🐓')) && palabrasSeguras.some(p => todoElTexto.includes(p))) {
        return { score: 0, motivo: "Contexto de comida detectado" };
    }

    // Si no tiene texto ni hashtags, es sospechoso por ofuscación
    if (!tiktok.text && (!tiktok.hashtags || tiktok.hashtags.length === 0)) {
        return { score: 35, motivo: "Posible ofuscación (Sin metadatos)" };
    }

    let score = 0;
    const palabras = todoElTexto.split(/\s+/);
    palabras.forEach(p => {
        const res = fuse.search(p);
        if (res.length > 0) score += res[0].item.peso;
    });

    if (todoElTexto.includes('🍕') && todoElTexto.includes('🐓')) score += 40;

    return { score, url: tiktok.webVideoUrl, motivo: "Análisis de términos y emojis" };
}

// 4. Lógica del Filtro Beta (Análisis de Comentarios)
function analizarComentariosBeta(comentarios) {
    const textoJunto = comentarios.join(" ").toLowerCase();

    // Búsqueda en una sola pasada con Aho-Corasick
    const hitsReclutamiento = acReclutamiento.search(textoJunto).length;
    const hitsAdmiracion = acAdmiracion.search(textoJunto).length;

    let nivelRiesgo = "ALTO (Pendiente)";
    if (hitsReclutamiento >= 2) nivelRiesgo = "CRÍTICO (Reclutamiento Activo)";
    else if (hitsAdmiracion >= 3) nivelRiesgo = "CRÍTICO (Idolatría Criminal)";

    return { hitsReclutamiento, hitsAdmiracion, nivelRiesgo };
}

// 5. Función Maestra: El Pipeline Alpha -> Beta
async function ejecutarProteccion404() {
    try {
        const rawData = fs.readFileSync('./scrapetest.json', 'utf-8');
        const tiktoks = JSON.parse(rawData);

        console.log(`\n🛡️ SISTEMA 404: Analizando ${tiktoks.length} videos...`);

        const prospectosBeta = [];

        // FASE 1: FILTRADO ALPHA
        tiktoks.forEach(t => {
            const res = evaluarReelAlpha(t);
            if (res.score >= 30) {
                prospectosBeta.push({ id: t.id, url: t.webVideoUrl, scoreAlpha: res.score });
            }
        });

        if (prospectosBeta.length === 0) {
            console.log("✅ No se detectaron amenazas en la Fase Alpha.");
            return;
        }

        console.log(`⚠️ Fase Alpha: ${prospectosBeta.length} videos sospechosos. Iniciando Fase Beta...`);

        // FASE 2: EXTRACCIÓN CON APIFY
        const urls = prospectosBeta.map(p => p.url);
        const run = await apifyClient.actor("clockworks/tiktok-comments-scraper").call({
            postURLs: urls,
            commentsPerPost: 30
        });

        const { items } = await apifyClient.dataset(run.defaultDatasetId).listItems();

        // Agrupar comentarios por URL de video
        const comentariosPorVideo = {};
        items.forEach(item => {
            if (!comentariosPorVideo[item.postURL]) comentariosPorVideo[item.postURL] = [];
            comentariosPorVideo[item.postURL].push(item.text);
        });

        // FASE 3: ANÁLISIS AHO-CORASICK Y REPORTE
        console.log("\n🚨 REPORTE FINAL DE AMENAZAS DETECTADAS:");
        console.log("==================================================");

        prospectosBeta.forEach(video => {
            const listaComentarios = comentariosPorVideo[video.url] || [];
            const analisisBeta = analizarComentariosBeta(listaComentarios);

            console.log(`[VIDEO ID: ${video.id}]`);
            console.log(`🔗 URL: ${video.url}`);
            console.log(`📊 Score Alpha: ${video.scoreAlpha}`);
            console.log(`💬 Análisis Beta: ${analisisBeta.nivelRiesgo}`);
            console.log(`   - Interacciones de reclutamiento: ${analisisBeta.hitsReclutamiento}`);
            console.log(`   - Frases de admiración: ${analisisBeta.hitsAdmiracion}`);
            console.log("--------------------------------------------------");
        });

    } catch (error) {
        console.error("🚨 Error en el Pipeline:", error.message);
    }
}

ejecutarProteccion404();