import { readFileSync } from 'fs';

function analizarPublicaciones() {
    try {
        const dataRaw = readFileSync('./scrapetest.json', 'utf-8');
        const tiktoks = JSON.parse(dataRaw);

        console.log(`\n==================================================`);
        console.log(`${tiktoks.length} total tiktoks collected.`);
        console.log(`==================================================\n`);

        // Segmentar y analizar cada publicación
        tiktoks.forEach((tiktok, index) => {
            // Extraer la descripción 'raw' (texto)
            const descripcion = tiktok.text ? tiktok.text.trim() : 'N/A (Sin descripción)';

            // Extraer el vector de hashtags
            let vectorHashtags = [];

            // Verificar que el arreglo de hashtags exista y tenga elementos
            if (tiktok.hashtags && Array.isArray(tiktok.hashtags) && tiktok.hashtags.length > 0) {
                // Se mapea el arreglo 
                vectorHashtags = tiktok.hashtags
                    .map(ht => ht.name)
                    .filter(name => name !== ""); // filtro de strings vacíos
            }

            console.log(`[Publicación ${index + 1}] | ID: ${tiktok.id}`);
            console.log(`Descripción: ${descripcion}`);

            if (vectorHashtags.length > 0) {
                console.log(`Hashtags detectados: [ '${vectorHashtags.join("', '")}' ]`);
            } else {
                console.log(`Hashtags detectados: [] (Nulos / Ninguno)`);
            }
            console.log('--------------------------------------------------');
        });

    } catch (error) {
        console.error("Error al leer o procesar el archivo:", error.message);
    }
}

analizarPublicaciones();