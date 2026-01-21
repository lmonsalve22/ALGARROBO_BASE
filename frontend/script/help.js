/**
 * Sistema de Ayuda - Modal de ayuda contextual para cada vista
 */

const helpContent = {
    dashboard: {
        title: 'Dashboard de Proyectos',
        icon: 'fa-chart-line',
        description: 'Panel principal de visualización y análisis de la cartera de proyectos municipales.',
        features: [
            'Visualiza KPIs principales: proyectos activos, inversión total, avance promedio y más',
            'Explora gráficos interactivos organizados por categorías: estado, área, financiamiento, etc.',
            'Consulta los últimos 10 proyectos modificados con sus detalles',
            'Los datos se actualizan automáticamente al cargar la página'
        ],
        tips: [
            'Pasa el cursor sobre los gráficos para ver detalles específicos',
            'Los valores monetarios están expresados en millones (M) o miles (K)',
            'El avance promedio considera todos los proyectos activos'
        ]
    },
    proyecto: {
        title: 'Gestión de Proyectos',
        icon: 'fa-folder-open',
        description: 'Módulo central para la administración integral del portafolio de proyectos municipales. Permite crear, editar, visualizar y analizar la cartera completa de iniciativas de inversión, facilitando la toma de decisiones estratégicas y el seguimiento detallado de cada proyecto.',
        features: [
            '📝 Crear nuevos proyectos con formulario completo: nombre, código, descripción, objetivo, monto total, fuente de financiamiento, área responsable y más',
            '✏️ Editar proyectos existentes con actualización de todos los campos: estado actual, avances, montos ejecutados, fechas clave',
            '🔍 Sistema de filtros avanzados: combina criterios por estado (diseño, licitación, ejecución, terminado), área municipal, profesional responsable, año de inicio, financiamiento',
            '🔎 Búsqueda inteligente en tiempo real por nombre, código, sector, descripción o cualquier campo visible en la tabla',
            '👥 Asignación de equipo de trabajo: hasta 5 profesionales responsables por proyecto con roles específicos (jefe de proyecto, coordinador, supervisor, etc.)',
            '📍 Geolocalización precisa: ingreso de coordenadas geográficas (latitud/longitud) para visualización en mapa',
            '📊 Registro de avance físico y financiero: actualización de porcentajes de ejecución y montos gastados vs. presupuestados',
            '📅 Gestión de fechas: inicio programado, inicio real, término programado, término real, próximos hitos',
            '💰 Control presupuestario: monto total, monto ejecutado, saldo disponible, proyecciones de gasto',
            '🏷️ Categorización múltiple: área, sector territorial, tipo de inversión, prioridad estratégica, beneficiarios',
            '📄 Exportación de datos: descarga la tabla filtrada en Excel (XLSX) o PDF con formato profesional',
            '🔄 Sincronización automática: los cambios se reflejan inmediatamente en dashboard, mapas, calendario e informes',
            '📋 Visualización de historial: registro de todas las modificaciones realizadas a cada proyecto con fecha y usuario',
            '🎯 Marcado de proyectos prioritarios: destaca iniciativas estratégicas para seguimiento especial',
            '📸 Adjuntar fotografías: vincula imágenes de avance físico, situación inicial y final del proyecto'
        ],
        tips: [
            '💡 Combina múltiples filtros para encontrar proyectos específicos (ejemplo: "Área: Vialidad + Estado: Ejecución + Año: 2025")',
            '💡 El campo de avance acepta valores decimales entre 0 y 1 (ejemplo: 0.75 = 75%). También puedes ingresar porcentajes directamente',
            '💡 Usa el botón "Limpiar Filtros" para volver a ver todos los proyectos de la cartera',
            '💡 Las coordenadas geográficas deben estar en formato decimal (ejemplo: Latitud: -33.456789, Longitud: -70.123456)',
            '💡 El código de proyecto es único y sirve como identificador en todos los módulos del sistema',
            '💡 Actualiza regularmente el estado y avance de cada proyecto para mantener la información al día',
            '💡 Los profesionales asignados recibirán notificaciones sobre cambios importantes en sus proyectos',
            '💡 Exporta la lista filtrada antes de reuniones o presentaciones para tener reportes actualizados',
            '💡 Los montos deben ingresarse en pesos chilenos (CLP) sin puntos ni comas, el sistema los formateará automáticamente',
            '💡 Haz doble clic en una fila para abrir rápidamente el modo de edición del proyecto'
        ]
    },
    informe: {
        title: 'Centro de Informes y Reportería',
        icon: 'fa-file-chart-line',
        description: 'Plataforma integral de generación de reportes profesionales para análisis de la cartera de proyectos. Produce documentos ejecutivos con datos actualizados, gráficos estadísticos, tablas dinámicas y resúmenes inteligentes generados por IA, facilitando la presentación de información a autoridades y stakeholders.',
        features: [
            '📊 10+ tipos de informes predefinidos: cartera completa, análisis por estado, distribución por área, análisis financiero, proyectos prioritarios, avance general, ejecución presupuestaria, cronograma de actividades, proyectos por profesional, situación territorial',
            '🎨 Múltiples formatos de salida: PDF profesional con diseño institucional, Excel editable con tablas dinámicas, visualización HTML interactiva',
            '🔧 Configuración de parámetros: selecciona área específica, filtro por profesional responsable, rango de años, estados a incluir, tipo de financiamiento',
            '🤖 Resumen ejecutivo con IA: cada informe PDF incluye un resumen analítico generado automáticamente que destaca los puntos clave, tendencias y recomendaciones',
            '📈 Gráficos automáticos integrados: tortas de distribución, barras de comparación, líneas de tendencia, mapas de calor, diagramas de Gantt',
            '📋 Tablas detalladas con indicadores: monto total, avance físico y financiero, plazos, responsables, estados críticos',
            '👁️ Vista previa interactiva: revisa el contenido del informe antes de generar el archivo final, con navegación por secciones',
            '📅 Información de generación: cada reporte incluye fecha, hora, usuario generador y parámetros de filtrado aplicados',
            '🔄 Actualización en tiempo real: los datos mostrados reflejan el estado actual de la cartera al momento de generar el informe',
            '📧 Opciones de distribución: envío directo por correo, descarga local, almacenamiento en la nube',
            '🎯 Informes personalizados: crea plantillas propias combinando diferentes secciones y métricas',
            '📊 Dashboard de informes: historial de reportes generados con opción de regenerar con datos actualizados',
            '🔍 Análisis comparativo: genera informes que comparan períodos, áreas o estados diferentes',
            '💾 Guardado de configuraciones: guarda tus filtros favoritos para generar informes recurrentes rápidamente',
            '🌐 Marca institucional: todos los informes incluyen logos, colores y formato oficial del municipio'
        ],
        tips: [
            '💡 Genera el "Informe de Cartera Completa" mensualmente para seguimiento de gestión y archivo histórico',
            '💡 El resumen de IA analiza automáticamente los datos y puede identificar proyectos en riesgo o tendencias importantes',
            '💡 Usa filtros específicos para crear informes focalizados (ejemplo: "Solo proyectos de Vialidad en Ejecución")',
            '💡 Los informes Excel permiten análisis posterior con tablas dinámicas y fórmulas personalizadas',
            '💡 La vista previa te ahorra tiempo: revisa primero antes de generar el documento final',
            '💡 Combina el informe financiero con análisis de avance físico para detectar desfases presupuestarios',
            '💡 Programa la generación automática de informes recurrentes para envío a autoridades cada fin de mes',
            '💡 Incluye siempre el período de análisis en el nombre del archivo (ejemplo: "Informe_Cartera_Enero_2025.pdf")',
            '💡 Los gráficos son editables en la versión Excel si necesitas personalizar presentaciones',
            '💡 Archiva los informes generados para crear un historial de evolución de la cartera',
            '💡 El informe por profesional es útil para evaluaciones de desempeño y distribución de carga laboral'
        ]
    },
    calendario: {
        title: 'Calendario de Eventos y Planificación',
        icon: 'fa-calendar-alt',
        description: 'Sistema de gestión temporal que centraliza todos los eventos, hitos, fechas clave y actividades relacionadas con los proyectos municipales. Permite visualizar la agenda completa, planificar recursos, anticipar hitos críticos y coordinar múltiples iniciativas simultáneas con visión integrada.',
        features: [
            '📅 Múltiples vistas de calendario: mensual (vista general), semanal (planificación detallada), diaria (agenda específica), lista cronológica',
            '🎯 Sincronización automática de hitos: todos los hitos registrados en proyectos aparecen automáticamente con código de colores según importancia',
            '➕ Creación manual de eventos: registra reuniones, visitas a terreno, presentaciones, licitaciones, entregas, inspecciones, inauguraciones',
            '🏷️ Categorización de eventos: hito de proyecto, reunión técnica, reunión con comunidad, licitación, inspección, entrega parcial, término de obra, inauguración, reunión de coordinación',
            '🎨 Código de colores personalizable: diferencia visualmente tipos de eventos (verde: hitos completados, naranja: próximos, rojo: atrasados, azul: reuniones)',
            '🔔 Sistema de recordatorios: configura alertas por correo o notificación en sistema 1 día, 3 días o 1 semana antes',
            '📝 Detalles completos por evento: título, descripción, proyecto asociado, responsable, ubicación, duración, asistentes, documentos adjuntos',
            '🔍 Filtros dinámicos: muestra solo eventos de un área específica, un profesional, un tipo de evento, o un proyecto particular',
            '🔗 Vinculación con proyectos: cada evento puede estar asociado a uno o varios proyectos para trazabilidad completa',
            '📊 Vista de carga de trabajo: identifica períodos con alta concentración de eventos para mejor planificación de recursos',
            '↔️ Navegación rápida: botones para avanzar/retroceder meses, ir a hoy, saltar a fecha específica',
            '📥 Exportación a formatos estándar: descarga el calendario en formato iCal o Google Calendar para sincronizar con agenda personal',
            '🔄 Actualización en tiempo real: los cambios en fechas de proyectos actualizan automáticamente el calendario',
            '👥 Vista por responsable: filtra eventos asignados a un profesional específico para ver su agenda',
            '📍 Geolocalización de eventos: asocia eventos con ubicaciones específicas para planificar traslados'
        ],
        tips: [
            '💡 Revisa la vista mensual cada lunes para planificar la semana de actividades',
            '💡 Los hitos importantes (licitaciones, entregas) se sincronizan automáticamente desde la gestión de proyectos',
            '💡 Usa colores consistentes: por ejemplo, siempre rojo para eventos críticos, verde para hitos completados',
            '💡 Registra reuniones con comunidad para documentar participación ciudadana y compromisos adquiridos',
            '💡 Configura recordatorios para eventos críticos como inicios de licitación o vencimientos de plazos',
            '💡 La vista semanal es ideal para coordinar equipos de inspección y visitas a terreno',
            '💡 Filtra por área para ver la agenda específica de cada unidad municipal',
            '💡 Exporta el calendario antes de vacaciones para coordinar coberturas y delegaciones',
            '💡 Vincula siempre los eventos a proyectos específicos para mantener trazabilidad completa',
            '💡 Usa la vista diaria para preparar la agenda del día con anticipación',
            '💡 Registra eventos recurrentes (reuniones semanales de coordinación) para no olvidarlos'
        ]
    },
    mapa: {
        title: 'Mapa Territorial de Proyectos',
        icon: 'fa-map-marked-alt',
        description: 'Plataforma de visualización geoespacial que muestra la distribución territorial de todos los proyectos municipales. Permite análisis geográfico de la inversión, identificación de zonas con mayor/menor cobertura, planificación territorial y comunicación visual del impacto de las iniciativas en el territorio comunal.',
        features: [
            '🗺️ Mapa interactivo de alta calidad: visualización sobre cartografía base OpenStreetMap con controles de zoom, pan y capas',
            '📍 Marcadores diferenciados: cada proyecto aparece con un pin personalizado según su estado (verde: ejecución, azul: diseño, gris: terminado)',
            '💬 Popups informativos: haz clic en cualquier marcador para ver ficha resumen con nombre, monto, estado, avance, profesional responsable',
            '🎯 Filtros geográficos: muestra solo proyectos de sectores específicos, áreas municipales, o rangos de inversión',
            '📏 Herramientas de medición: mide distancias entre proyectos, calcula áreas de influencia, traza rutas',
            '🌍 Capas de información territorial: límite urbano, sectores censales, equipamiento público, áreas protegidas, zonificación PRC',
            '🔍 Búsqueda geográfica: localiza proyectos por dirección, sector o cercanía a un punto de referencia',
            '📊 Análisis de clusters: identifica zonas con concentración de proyectos para análisis de inversión territorial',
            '📐 Visualización de polígonos: muestra áreas de intervención de proyectos que abarcan zonas amplias (pavimentaciones, parques, etc.)',
            '🎨 Código de colores por monto: gradiente visual que muestra proyectos de mayor inversión en colores más intensos',
            '📷 Street View integrado: accede a vistas de calle para contextualizar la ubicación de cada proyecto',
            '📱 Responsive design: funciona perfectamente en escritorio, tablet y móvil para inspecciones en terreno',
            '🔄 Sincronización automática: actualización en tiempo real de ubicaciones cuando se modifican coordenadas en gestión de proyectos',
            '📥 Exportación de mapas: descarga capturas de pantalla del mapa actual con leyenda y escala incluidas',
            '🌐 Compartir ubicaciones: genera enlaces directos a proyectos específicos en el mapa para compartir con stakeholders'
        ],
        tips: [
            '💡 Solo aparecen proyectos que tienen coordenadas geográficas registradas en el módulo de gestión',
            '💡 Haz zoom para ver proyectos cercanos que pueden estar superpuestos en vistas alejadas',
            '💡 Usa las capas territoriales para analizar la relación de proyectos con zonificación y planificación urbana',
            '💡 Los colores de los pines ayudan a identificar rápidamente el estado de proyectos en cada sector',
            '💡 Genera mapas impresos para presentaciones a concejo o reuniones con la comunidad',
            '💡 El análisis de clusters ayuda a identificar sectores con sobre o sub inversión',
            '💡 Combina el filtro de área con el mapa para ver la distribución territorial de cada unidad municipal',
            '💡 Usa el scroll del mouse para hacer zoom, o los botones + - para control preciso',
            '💡 Haz clic derecho en el mapa para obtener coordenadas de cualquier punto',
            '💡 Activa varias capas simultáneamente para análisis territorial complejo',
            '💡 Exporta el mapa anual para documentar la cobertura territorial de la inversión municipal'
        ]
    },
    hitos: {
        title: 'Gestión de Hitos y Fechas Clave',
        icon: 'fa-flag',
        description: 'Sistema especializado para registrar, monitorear y controlar los hitos críticos de cada proyecto. Permite establecer fechas planificadas vs. reales, documentar el cumplimiento de etapas, generar alertas de retrasos y mantener un historial completo de avances, facilitando el control de gestión y la rendición de cuentas.',
        features: [
            '🎯 Creación de hitos estructurados: asocia cada hito a un proyecto específico con categoría predefinida (inicio, licitación, adjudicación, inicio obras, entrega parcial, término, recepción)',
            '📅 Registro de fechas múltiples: fecha planificada original, fecha reprogramada (si aplica), fecha real de cumplimiento, alertas de anticipación',
            '📝 Documentación detallada: descripción del hito, observaciones, documentos respaldo, fotografías de evidencia, responsable del registro',
            '🏷️ Categorización avanzada: tipo de hito (administrativo, técnico, financiero), criticidad (alta, media, baja), estado (pendiente, en proceso, completado, retrasado)',
            '📊 Historial completo por proyecto: visualiza cronológicamente todos los hitos de un proyecto con indicadores de cumplimiento',
            '🔔 Sistema de alertas automáticas: notificaciones por correo cuando se acerca la fecha de un hito crítico (7 días, 3 días, 1 día antes)',
            '📈 Indicadores de desempeño: porcentaje de hitos cumplidos en plazo, promedio de días de retraso, tasa de cumplimiento por área',
            '🔍 Filtros multidimensionales: busca por proyecto, categoría de hito, rango de fechas, estado, profesional responsable',
            '🔗 Sincronización con calendario: todos los hitos aparecen automáticamente en el calendario general del sistema',
            '💬 Comentarios y seguimiento: registra observaciones sobre el cumplimiento o incumplimiento de cada hito',
            '📄 Exportación de cronogramas: descarga el historial de hitos en Excel o PDF para reportes de avance',
            '🎨 Visualización tipo timeline: línea de tiempo gráfica que muestra la secuencia planned vs. real de hitos',
            '🔄 Actualización masiva: marca múltiples hitos como completados simultáneamente con fecha y evidencia',
            '📊 Dashboard de hitos: panel con próximos hitos críticos, hitos retrasados, hitos del mes',
            '🗂️ Plantillas de hitos: crea sets predefinidos de hitos típicos para cada tipo de proyecto (obras, estudios, adquisiciones)'
        ],
        tips: [
            '💡 Registra tanto la fecha planificada como la real para calcular automáticamente desvíos de programación',
            '💡 Categoriza correctamente cada hito para que las alertas lleguen a los responsables pertinentes',
            '💡 Usa observaciones detalladas para documentar razones de retrasos o cambios de programación',
            '💡 Los hitos críticos (inicio de licitación, entrega de obra) deben tener máxima prioridad de seguimiento',
            '💡 Adjunta documentos de respaldo (actas, certificados) al registrar el cumplimiento de hitos importantes',
            '💡 Revisa semanalmente el panel de próximos hitos para anticipar acciones y coordinar recursos',
            '💡 Configura alertas para hitos financieros (vencimientos de pagos, rendiciones) que son particularmente críticos',
            '💡 El historial de hitos es fundamental para auditorías y evaluaciones de gestión',
            '💡 Usa las plantillas para agilizar la creación de hitos en proyectos similares',
            '💡 Exporta el cronograma de hitos para incluir en informes de avance mensuales',
            '💡 Marca los hitos completados con evidencia fotográfica para documentación visual del avance'
        ]
    },
    observacion: {
        title: 'Sistema de Observaciones y Minutas',
        icon: 'fa-comment-alt',
        description: 'Plataforma colaborativa para documentar notas, comentarios, observaciones técnicas, acuerdos, compromisos y decisiones relacionadas con cada proyecto. Funciona como una bitácora digital que mantiene el registro histórico de todas las comunicaciones relevantes, facilitando la trazabilidad, transparencia y gestión del conocimiento institucional.',
        features: [
            '📝 Creación de observaciones estructuradas: vincula cada registro a un proyecto específico con fecha, autor, tipo y contenido',
            '🏷️ Tipos de observación predefinidos: observación técnica, acuerdo de reunión, compromiso, alerta, cambio de alcance, decisión de diseño, consulta ciudadana, hallazgo de inspección',
            '👤 Atribución automática: cada observación registra automáticamente quién la creó, fecha, hora y contexto',
            '📊 Historial cronológico completo: visualiza todas las observaciones de un proyecto ordenadas por fecha, con búsqueda y filtrado',
            '🔍 Búsqueda avanzada: encuentra observaciones por palabra clave en contenido, proyecto, autor, tipo o rango de fechas',
            '💬 Hilos de conversación: las observaciones pueden tener respuestas y comentarios, creando threads informativos',
            '📎 Adjuntos multimedia: anexa documentos PDF, imágenes, planos, correos electrónicos como respaldo de cada observación',
            '🔔 Menciones y notificaciones: menciona a usuarios específicos (@usuario) para que reciban alertas de observaciones importantes',
            '🎯 Marcado de prioridad: clasifica observaciones como urgente, importante o informativa para seguimiento diferenciado',
            '📋 Estado de observación: pendiente, en revisión, resuelta, descartada - permite hacer seguimiento de cierre',
            '📊 Panel de observaciones pendientes: dashboard que muestra observaciones sin resolver por proyecto o responsable',
            '🔄 Sincronización con workflow: las observaciones críticas pueden generar tareas automáticas en el sistema',
            '📄 Exportación de minutas: genera documentos Word o PDF con todas las observaciones de un proyecto o período',
            '🔐 Niveles de privacidad: observaciones públicas (todo el equipo) y privadas (solo involucrados)',
            '📅 Integración con calendario: observaciones con fecha de seguimiento aparecen como recordatorios en calendario'
        ],
        tips: [
            '💡 Usa observaciones inmediatamente después de reuniones importantes para no olvidar acuerdos y compromisos',
            '💡 Las observaciones técnicas de inspecciones son evidencia clave para control de calidad y resolución de conflictos',
            '💡 Menciona a profesionales responsables para que reciban notificación y puedan responder o tomar acción',
            '💡 Adjunta siempre evidencia (fotos, planos marcados) cuando registres observaciones técnicas en terreno',
            '💡 Marca como "urgente" solo observaciones que requieren acción inmediata para no saturar de alertas',
            '💡 Revisa regularmente el panel de observaciones pendientes para dar seguimiento a compromisos',
            '💡 Las observaciones forman un registro histórico valioso para futuras licitaciones y proyectos similares',
            '💡 Usa tipos específicos de observación para facilitar búsquedas posteriores (ej: filtrar solo "acuerdos de reunión")',
            '💡 Exporta las observaciones de un proyecto terminado como lección aprendida para futuros proyectos',
            '💡 Las observaciones ciudadanas deben responderse y marcarse como resueltas para rendición de cuentas',
            '💡 Crea un hilo de observaciones relacionadas en vez de múltiples registros separados para mejor trazabilidad'
        ]
    },
    documento: {
        title: 'Repositorio de Documentos de Proyectos',
        icon: 'fa-file-alt',
        description: 'Sistema centralizado de gestión documental que organiza, almacena y proporciona acceso seguro a todos los archivos relacionados con los proyectos municipales. Incluye estudios técnicos, planos, contratos, informes, fotografías, permisos y cualquier documento relevante, con control de versiones, búsqueda avanzada y visor integrado.',
        features: [
            '📤 Carga de documentos multiformato: soporta PDF, Word, Excel, imágenes (JPG, PNG), AutoCAD (DWG, DXF), archivos comprimidos (ZIP, RAR)',
            '🏷️ Categorización detallada: clasifica documentos por tipo (estudio técnico, plano, contrato, presupuesto, informe de avance, fotografía, permiso, licitación, acta, correspondencia)',
            '🔗 Vinculación a proyectos: asocia cada documento a uno o varios proyectos específicos para organización y búsqueda',
            '📝 Metadata completa: registra nombre descriptivo, descripción, tipo, fecha de creación, versión, autor, palabras clave',
            '👁️ Visor integrado: visualiza PDFs, imágenes y documentos directamente en el navegador sin necesidad de descargar',
            '💾 Descarga individual o masiva: descarga un documento, varios seleccionados, o todos los de un proyecto en archivo ZIP',
            '🔍 Búsqueda multifacética: busca por nombre, tipo, proyecto, fecha, autor, contenido (OCR en PDFs), palabras clave',
            '📊 Filtros combinados: área, tipo de documento, rango de fechas, tamaño de archivo, proyecto',
            '🔄 Control de versiones: sube nuevas versiones manteniendo el historial completo con comparación de cambios',
            '📋 Historial de accesos: registro de quién abrió o descargó cada documento con fecha y hora',
            '🔐 Permisos granulares: define quién puede ver, descargar, editar o eliminar cada documento',
            '📎 Múltiples documentos simultáneos: carga varias archivos a la vez con drag & drop',
            '🏷️ Etiquetado colaborativo: agrega tags personalizados para organización adicional',
            '📸 Galería de fotos: vista especial para documentos tipo imagen, con slideshow y comparación antes/después',
            '🔔 Notificaciones de nuevos documentos: alertas automáticas al equipo cuando se suben documentos críticos',
            '📊 Estadísticas de repositorio: tamaño total, documentos por tipo, documentos más descargados, actividad reciente'
        ],
        tips: [
            '💡 Usa nombres descriptivos y específicos: "Plano_Arquitectura_Plaza_v3.pdf" en vez de "plano3.pdf"',
            '💡 Los documentos grandes (>10MB) pueden tardar en cargarse, considera comprimirlos si es posible',
            '💡 Categoriza correctamente para facilitar búsquedas futuras y cumplir con archivo municipal',
            '💡 Sube versiones actualizadas en vez de duplicar documentos para mantener orden y ahorrar espacio',
            '💡 Las fotografías de avance físico son evidencia valiosa, súbelas regularmente con fechas claras',
            '💡 Usa el visor integrado antes de descargar para verificar que es el documento correcto',
            '💡 Los planos técnicos deben incluir en la descripción la especialidad (arquitectura, estructuras, instalaciones)',
            '💡 Descarga todos los documentos de un proyecto en ZIP antes de licitaciones o entregas importantes',
            '💡 Elimina regularmente documentos obsoletos o duplicados para liberar espacio de almacenamiento',
            '💡 Agrega palabras clave relevantes en la descripción para mejorar las búsquedas',
            '💡 Los contratos y documentos legales deben tener máxima prioridad de respaldo y control de acceso',
            '💡 Establece una nomenclatura estándar de archivos para todo el equipo (ejemplo: TIPO_PROYECTO_DESCRIPCION_VERSION)'
        ]
    },
    geomapas: {
        title: 'Gestión de Capas Geográficas (GeoJSON)',
        icon: 'fa-draw-polygon',
        description: 'Herramienta especializada para la administración de información geoespacial avanzada de los proyectos. Permite crear, importar, visualizar y analizar geometrías vectoriales (polígonos, líneas, puntos) en formato GeoJSON, representando áreas de intervención, trazados de obras lineales, límites de proyectos y zonas de influencia con precisión cartográfica.',
        features: [
            '🗺️ Creación de geometrías GeoJSON: define polígonos de áreas de intervención, líneas de trazados (calles, redes), puntos de interés múltiples',
            '📤 Importación de archivos: carga GeoJSON creados en herramientas externas (QGIS, ArcGIS, Google Earth Pro)',
            '🔗 Asociación a proyectos: vincula cada geomapa a uno o varios proyectos para análisis territorial integrado',
            '📝 Metadata geográfica: nombre de la capa, descripción, sistema de coordenadas, propiedades alfanuméricas',
            '🎨 Estilos personalizables: define colores de relleno, borde, transparencia, grosor de línea para visualización',
            '👁️ Visor cartográfico integrado: visualiza las geometrías sobre mapa base con zoom, pan y mediciones',
            '📐 Herramientas de análisis espacial: cálculo de áreas, perímetros, longitudes, centroides',
            '🔍 Consultas espaciales: identifica proyectos dentro de un polígono, cercanía a vías, superposiciones',
            '📊 Tabla de atributos: cada feature en el GeoJSON puede tener propiedades alfanuméricas (nombre, tipo, etc.)',
            '💾 Exportación estándar: descarga las geometrías en formato GeoJSON estándar para uso en otros sistemas SIG',
            '🔄 Sincronización con mapa principal: las geometrías aparecen automáticamente en el módulo de mapa de proyectos',
            '📏 Validación geométrica: el sistema verifica que las geometrías sean válidas según estándar OGC',
            '🌐 Soporte multi-proyección: importa GeoJSON en diferentes sistemas de coordenadas con reproyección automática',
            '📋 Historial de capas: mantiene versiones anteriores de geometrías para control de cambios',
            '🎯 Casos de uso: áreas de parques, trazados de pavimentación, límites de intervención, zonas de beneficiarios, cobertura de servicios'
        ],
        tips: [
            '💡 Los geomapas permiten representar proyectos que no son puntuales sino áreas completas (parques, pavimentaciones)',
            '💡 Puedes crear GeoJSON en QGIS (software libre) y subirlos directamente al sistema',
            '💡 Verifica siempre que el sistema de coordenadas sea WGS84 (EPSG:4326) para compatibilidad',
            '💡 Las propiedades del GeoJSON (nombre de calle, tipo de superficie) se muestran al hacer clic en el mapa',
            '💡 Usa colores diferenciados para distinguir tipos de intervención (verde: áreas verdes, gris: pavimentos)',
            '💡 Los polígonos de intervención son útiles para calcular beneficiarios según densidad poblacional',
            '💡 Exporta los geomapas para compartir con otros departamentos o instituciones externas',
            '💡 Las geometrías lineales (redes de agua, vías) deben tener propiedades de longitud para cubicación',
            '💡 Mantén las geometrías simples: polígonos muy complejos cargan lento en el visor',
            '💡 Documenta en la descripción la fuente de la geometría (levantamiento GPS, digitalización de plano, etc.)',
            '💡 Usa geomapas para planificación: superpone áreas de proyectos futuros con servicios existentes'
        ]
    },
    user: {
        title: 'Gestión de Usuarios',
        icon: 'fa-users-cog',
        description: 'Administra los usuarios del sistema y sus permisos.',
        features: [
            'Ver listado de usuarios registrados',
            'Crear nuevos usuarios con diferentes roles',
            'Editar información de usuarios existentes',
            'Activar o desactivar cuentas de usuario'
        ],
        tips: [
            'Los roles determinan los permisos de cada usuario',
            'Mantén actualizados los datos de contacto',
            'Solo administradores pueden gestionar usuarios'
        ]
    },
    analisis: {
        title: 'Análisis de Datos',
        icon: 'fa-analytics',
        description: 'Herramientas avanzadas de análisis de la cartera de proyectos.',
        features: [
            'Análisis estadístico de proyectos',
            'Comparativas entre períodos',
            'Indicadores de gestión',
            'Tendencias y proyecciones'
        ],
        tips: [
            'Usa filtros para análisis más específicos',
            'Los gráficos son interactivos',
            'Exporta los resultados del análisis'
        ]
    },
    chat: {
        title: 'Asistente IA',
        icon: 'fa-robot',
        description: 'Consulta información sobre proyectos usando inteligencia artificial.',
        features: [
            'Haz preguntas en lenguaje natural sobre los proyectos',
            'Obtén resúmenes y análisis automáticos',
            'Consulta datos específicos de manera conversacional',
            'Historial de conversaciones'
        ],
        tips: [
            'Sé específico en tus preguntas para mejores respuestas',
            'Puedes preguntar sobre montos, estados, profesionales, etc.',
            'El asistente tiene acceso a todos los datos de proyectos'
        ]
    },
    vecinos: {
        title: 'App Vecinos - Reportes Ciudadanos',
        icon: 'fa-users',
        description: 'Plataforma de visualización y gestión de reportes ciudadanos. Permite monitorear, revisar y actualizar el estado de las denuncias realizadas por los vecinos de la comuna a través de la aplicación móvil.',
        features: [
            '🗺️ Mapa interactivo con todos los reportes ciudadanos geolocalizados',
            '📊 Tarjetas de estadísticas: total de reportes, pendientes, verificados, en proceso y resueltos',
            '🔍 Filtros avanzados: por categoría (bache, luminaria, basura, etc.), estado, gravedad y rango de fechas',
            '📋 Listado de reportes con vista previa de información clave',
            '✏️ Edición de reportes: cambiar estado, gravedad, categoría, marcar como revisado',
            '👁️ Panel de detalles completo con información del ciudadano que reportó',
            '🎨 Marcadores de colores según estado del reporte para identificación rápida',
            '📍 Geolocalización precisa de cada reporte con coordenadas',
            '📅 Registro de fechas de creación y última actualización',
            '🔔 Seguimiento del flujo de trabajo: Reportado → Verificado → Programado → Reparado'
        ],
        tips: [
            '💡 Los colores de los marcadores indican el estado: naranja (reportado), azul (verificado), violeta (programado), verde (reparado)',
            '💡 Usa los filtros de fecha para analizar reportes de un período específico',
            '💡 Haz clic en un reporte del listado para centrarlo en el mapa',
            '💡 Desde el panel de detalles puedes editar el estado y gravedad del reporte',
            '💡 Los reportes resueltos incluyen los estados "Reparado" y "Cerrado"',
            '💡 Marca como "Revisado" cuando hayas verificado en terreno',
            '💡 La descripción del ciudadano puede contener información importante para la gestión'
        ]
    }
};

// Función para mostrar el modal de ayuda
function showHelpModal(viewName) {
    const content = helpContent[viewName] || helpContent.dashboard;

    // Crear modal si no existe
    let modal = document.getElementById('helpModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'helpModal';
        modal.innerHTML = `
            <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex items-center justify-center p-4" onclick="closeHelpModal(event)">
                <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden" onclick="event.stopPropagation()">
                    <div class="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 p-6 text-white">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-4">
                                <div class="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur">
                                    <i class="fas ${content.icon} text-xl"></i>
                                </div>
                                <div>
                                    <h2 class="text-2xl font-bold" id="helpModalTitle">${content.title}</h2>
                                    <p class="text-white/80 text-sm">Guía de ayuda</p>
                                </div>
                            </div>
                            <button onclick="closeHelpModal()" class="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center hover:bg-white/30 transition-colors">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="p-6 overflow-y-auto max-h-[60vh]" id="helpModalContent">
                        <!-- Content will be inserted here -->
                    </div>
                    <div class="border-t border-gray-100 p-4 bg-gray-50 flex justify-end">
                        <button onclick="closeHelpModal()" class="px-6 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors font-medium">
                            <i class="fas fa-check mr-2"></i>Entendido
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // Actualizar contenido
    document.getElementById('helpModalTitle').textContent = content.title;
    document.querySelector('#helpModal .fa-robot, #helpModal .fa-chart-line, #helpModal .fa-folder-open, #helpModal .fa-file-chart-line, #helpModal .fa-calendar-alt, #helpModal .fa-map-marked-alt, #helpModal .fa-flag, #helpModal .fa-comment-alt, #helpModal .fa-file-alt, #helpModal .fa-draw-polygon, #helpModal .fa-users-cog, #helpModal .fa-analytics')?.classList.remove('fa-robot', 'fa-chart-line', 'fa-folder-open', 'fa-file-chart-line', 'fa-calendar-alt', 'fa-map-marked-alt', 'fa-flag', 'fa-comment-alt', 'fa-file-alt', 'fa-draw-polygon', 'fa-users-cog', 'fa-analytics');

    const contentHtml = `
        <div class="mb-6">
            <p class="text-gray-600 text-lg leading-relaxed">${content.description}</p>
        </div>
        
        <div class="mb-6">
            <h3 class="font-bold text-gray-800 mb-3 flex items-center gap-2">
                <i class="fas fa-list-check text-indigo-500"></i>
                ¿Qué puedes hacer aquí?
            </h3>
            <ul class="space-y-2">
                ${content.features.map(f => `
                    <li class="flex items-start gap-3 text-gray-600">
                        <i class="fas fa-check-circle text-green-500 mt-1 flex-shrink-0"></i>
                        <span>${f}</span>
                    </li>
                `).join('')}
            </ul>
        </div>
        
        <div class="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <h3 class="font-bold text-amber-800 mb-2 flex items-center gap-2">
                <i class="fas fa-lightbulb text-amber-500"></i>
                Consejos útiles
            </h3>
            <ul class="space-y-1">
                ${content.tips.map(t => `
                    <li class="flex items-start gap-2 text-amber-700 text-sm">
                        <i class="fas fa-angle-right mt-1 flex-shrink-0"></i>
                        <span>${t}</span>
                    </li>
                `).join('')}
            </ul>
        </div>
    `;

    document.getElementById('helpModalContent').innerHTML = contentHtml;
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// Función para cerrar el modal
function closeHelpModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('helpModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Cerrar con ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeHelpModal();
});

// Función para crear el botón de ayuda
function createHelpButton(viewName) {
    const btn = document.createElement('button');
    btn.id = 'helpButton';
    btn.className = 'fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all z-40 flex items-center justify-center group';
    btn.innerHTML = `
        <i class="fas fa-question text-xl"></i>
        <span class="absolute right-full mr-3 bg-gray-800 text-white text-sm px-3 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            Ayuda
        </span>
    `;
    btn.onclick = () => showHelpModal(viewName);
    document.body.appendChild(btn);
}
