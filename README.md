# HCKMX26-CyShells
Hackathon 404. Threat Not Found proposal

### Inverted Christmas Tree

***Descripción:*** Este algoritmo funciona como un embudo de filtrado descendente. Comienza con un amplio análisis de los hashtags y descripciones en videos de TikTok mediante una búsqueda difusa, para luego analizar los comentarios en base a un diccionario preestablecido, y finalizar utilizando *computer visión* para detectar patrones referentes a los grupos criminales en las portadas de los videos. De esta forma, dado un *sample* de videos en TikTok, el algoritmo "Inverted Christmas Tree" es capaz de discernir entre videos inofensivos y videos con un índole criminal. 



***Problema:*** La problemática central de este proyecto es la ausencia de herramientas tecnológicas para la detección temprana de riesgos asociados a la narcocultura en plataformas digitales. Actualmente, las redes sociales carecen de mecanismos eficaces para identificar de forma proactiva dos fenómenos críticos:

&#x09;- El reclutamiento digital: El uso de plataformas como TikTok para captar jóvenes mediante mensajes codificados.

&#x09;- La admiración/idrolatración de la narcocultura: La propagación de contenido que normaliza y ensalza estilos de vida delictivos.

Debido a la magnitud del contenido generado, el problema se vuelve inabordable manualmente. Por ello, nuestro algoritmo busca automatizar el filtrado de los videos, detectando patrones de riesgo en hashtags, descripciones e imágenes que los filtros convencionales suelen pasar por alto.





***Tecnologías y Herramientas ocupadas:***

* **Lenguajes de programación:**

&#x09;- Python

&#x09;- JavaScript

&#x09;- SQL

&#x09;- HTML

&#x09;- CSS



* **Tecnologías:**

&#x09;**-** Apify

&#x09;- AWS (Cloud9, EC2 y RDS)



* **Librerías:**

&#x09;**-** JavaScript (fuse.js, aho-corasick, apify-client)

&#x09;- Python(cv2, torch, ultralytics, numpy, yt\_dlp, requests)
    &#x09;- cv2: es la librería que se encarga de manipular la imagen. Con esto, abrimos archivos, cambiamos colores, se dibujan los cuadros de alerta y los textos, mostrando de manera final una ventana con el resultado.
    &#x09;- torch: es la base sobre la que corre YOLO. Gestiona los calculos complejos en el procesador o en la tarjeta de vídeo para que la deteccion sea instantanea.
    &#x09;- ultralytics: es un detector de objetos. Observa o analiza la imagen, por asi decirlo, y nos dice qué es lo que hay; en este caso, buscando un rifle, una persona o un camión; y también nos indica en que coordenadas está.
    &#x09;- numpy: permite que el código procese los miles de números que contiene una imagen para que pueda calcular porcentajes de color de una imagen, o interpretar a qué pertenece una silueta. 
    &#x09;- yt_dlp: es una herramienta de linea de comandos que extrae y descarga video de los sitios web. En nuestro caso, se encarga de burlar las protecciones (requests) que a veces tienen los sistemas de seguridad que las plataformas presentan, entonces entra al link y extrae el archivo multimedia real.
    &#x09;- requests:  ayuda a que el programa se dirija a una URL, y descargue los datos de la imagen, para que después se puedan transformar en algo visible.



***Instrucciones para la ejecución del prototipo:***

**Paso 1:** Generación de Token. Para obtener tu token de API de Apify, inicia sesión en la consola de Apify y dirígete a Settings (Configuración) > Integrations (Integraciones). Allí encontrarás tu Personal API Token, el cual puedes copiar para autenticar tus solicitudes de API, integraciones con n8n, Make u otros servicios.
**Paso 2:** Una vez copiado el Token de apify, dirígete al archivo script.mjs y modifica el atriuto token del objeto ApifyClient (dentro de la instrucción: const apifyClient = new ApifyClient({
    token: "your_apify_token"
});).
**Paso 3:** ingresa la contraseña y demás configuraciones de tu instancia de base de datos (dado a que este es un repositorio público, se ha resguardado la contraseña de la base de datos del proyecto debajo de una variable de entorno, por lo que si se quiere replicar este proyecto, es necesario crear una instancia personal de base de datos con el motor MySQL siguiendo las declaraciones del script hack_shell.sql).
**Paso 4:** Descargar todos los archivos del repositorio HCKMX26-1776750078
**Paso 5:** Abrir la carpeta del repositorio en su computadora. Copiar la dirección a esa carpeta
**Paso 6:** Abrir terminal Windows PowerShell (o equivalente dependiendo del sistema operativo). Escribir el siguiente comando en la terminal y darle enter: npm install express mysql2 cors
**Paso 7:** Escribir en la terminal y darle enter: cd [Dirección de la carpeta del repositorio en su computadora]
**Paso 8:** Escribir en la terminal y darle enter: node server.mjs El mensaje “🚀 Servidor Dashboard iniciado en http://localhost:3000 📡 Conectado a la DB RDS: hack_shell” aparece; significa que todo ocurrió correctamente. 
**Paso 9:** Abrir el archivo dashboard-tiktok en su browser de preferencia. 


***IA Utilizadas:***

* Gemini: Utilizada principalmente paara el debuggeo de todos los códigos. No obstante, nos ayudó a resolver multiples problemas como la conexión entre la base de datos y nuestro dashboard, y la implementación de Apify en nuestro algoritmo. 
* Cursor: El dashboard fue realizado en su mayoría con ayuda de esta IA; específicamente, el apartado de las gráficas, los filtros y el buscador. 

***Video demostrativo del proyecto***

https://drive.google.com/file/d/1rZcIS7fDMx84hCngKRJi5QlDoThlLAiW/view?usp=sharing


***Integrantes del equipo:***

* Alexander Mejia Tovar
* Jebrana Yatziri Balvanera Chumacero
* Alejandra López De la Cruz

