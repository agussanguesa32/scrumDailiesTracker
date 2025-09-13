# Dailies Bot - Discord Bot para Stand-ups Diarios

Bot de Discord modular y configurable para gestionar dailies y stand-ups diarios siguiendo metodología ágil. Automatiza el envío de recordatorios, recolección de respuestas y seguimiento del equipo.

## Características Principales

### 🤖 Automatización Completa
- **Recordatorios automáticos**: Envío programado de DMs personalizados a miembros del equipo
- **Horarios configurables**: Define días de la semana y horarios específicos
- **Recordatorios secundarios**: Sistema opcional de recordatorios para quienes no completaron su daily
- **Resumen diario**: Mensaje automático al final del día con usuarios faltantes

### 💬 Interfaz de Usuario Intuitiva
- **Formularios modales**: 4 preguntas clave del stand-up en formato interactivo
- **Botones persistentes**: Los botones de DM funcionan incluso después de reinicios del bot
- **Configuración visual**: Select menus para selección de días, sin necesidad de escribir
- **Mensajes formateados**: Respuestas enviadas al canal con formato profesional

### ⚙️ Gestión y Configuración
- **Panel de administración**: Comando `/setup` con interfaz completa de configuración
- **Roles flexibles**: Soporte para múltiples roles de equipo configurables
- **Persistencia de datos**: Configuración y respuestas guardadas automáticamente
- **Comandos de estado**: Seguimiento de participación y estadísticas

### 🔧 Arquitectura Modular
- **Sistema de Cogs**: Funcionalidades organizadas en módulos independientes
- **Configuración dinámica**: Cambios en tiempo real sin reiniciar el bot
- **Almacenamiento JSON**: Datos persistentes en archivos locales
- **Logs detallados**: Sistema de logging para debugging y monitoreo

## Instalación y Configuración

### Requisitos Previos
- Python 3.8+
- Bot de Discord configurado en Discord Developer Portal
- Permisos de administrador en el servidor Discord

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd dailies-bot
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**
```bash
cp .env.template .env
```

4. **Completar configuración en `.env`**
```env
# Token del bot (Discord Developer Portal)
DISCORD_TOKEN=your_bot_token_here

# IDs de servidor y canales
GUILD_ID=your_guild_id
DAILIES_CHANNEL_ID=your_channel_id

# Roles del equipo (separados por coma)
PRODUCT_TEAM_ROLES=role_id1,role_id2,role_id3

# Rol de administrador
ADMIN_ROLE_ID=admin_role_id

# Configuración de zona horaria
TIMEZONE=America/Buenos_Aires

# Horarios por defecto (modificables desde /setup)
DAILY_HOUR=10
DAILY_MINUTE=0
```

5. **Ejecutar el bot**
```bash
python main.py
```

## Comandos y Funcionalidades

### Comandos de Administración
- **`/setup`** - Panel completo de configuración
  - Configurar días activos con select menu visual
  - Establecer horarios de envío y recordatorios
  - Activar/desactivar el sistema
  - Ver configuración actual
- **`/test_daily`** - Enviar recordatorios de prueba
- **`/daily_reminder`** - Enviar recordatorios manuales

### Comandos de Usuario
- **`/daily`** - Completar daily manualmente
- **`/daily_status`** - Ver estado del equipo (quién completó/falta)

## Arquitectura del Sistema

### Estructura de Archivos
```
dailies-bot/
├── main.py                    # Punto de entrada y configuración del bot
├── requirements.txt           # Dependencias Python
├── .env.template             # Template de configuración
│
├── cogs/                     # Módulos funcionales
│   ├── setup_commands.py     # Comandos de configuración y administración
│   ├── daily_commands.py     # Comandos de usuario para dailies
│   └── daily_scheduler.py    # Sistema de tareas programadas y modals
│
├── utils/                    # Utilidades y configuración
│   └── config.py            # Gestión de configuración, almacenamiento y utilidades
│
└── data/                    # Almacenamiento persistente (auto-creado)
    ├── schedule.json        # Configuración de horarios y días activos
    └── dailies.json        # Registro temporal de dailies (se limpia diariamente)
```

### Flujo de Funcionamiento

1. **Inicio del día**: Bot envía mensaje con fecha al canal y DMs a usuarios
2. **Interacción**: Usuarios completan daily mediante botón persistente
3. **Procesamiento**: Respuestas se formatean y envían al canal del equipo
4. **Seguimiento**: Sistema tracking de quién completó/falta
5. **Recordatorio**: Opcional segundo recordatorio en horario configurado
6. **Fin del día**: Resumen de usuarios faltantes y limpieza de datos

## Preguntas del Formulario Daily

El modal interactivo incluye:

1. **Estado personal**: "¿Cómo te sentís hoy? ✨ ¿Dormiste bien? 😴"
2. **Trabajo anterior**: "¿Qué hiciste ayer? ¿Moviste alguna card?"
3. **Planificación**: "¿Qué vas a hacer hoy?"
4. **Bloqueos**: "¿Necesitás ayuda con algo? ¿Bloqueos? ¿PRs?"

## Personalización y Extensión

### Variables Configurables
- **Zona horaria**: Configurable por variable de entorno
- **Roles de equipo**: Soporte para múltiples roles
- **Horarios**: Configuración granular de horarios de envío y recordatorios
- **Días activos**: Selección flexible de días de la semana

### Extensibilidad
- **Nuevos comandos**: Agregar fácilmente nuevos cogs
- **Personalización de preguntas**: Modificar formulario en `daily_scheduler.py`
- **Integración**: Sistema modular permite integrar con otras herramientas
- **Almacenamiento**: Fácil migración a bases de datos si se requiere

## Permisos de Discord Requeridos

- **Enviar mensajes**: Para respuestas en canales
- **Mensajes embebidos**: Para formato visual de dailies
- **Enviar DMs**: Para recordatorios personales
- **Ver miembros**: Para identificar roles del equipo
- **Comandos de aplicación**: Para comandos slash
- **Leer historial**: Para contexto de mensajes

## Consideraciones de Seguridad

- **Variables sensibles**: Token y IDs en archivo `.env` (no versionar)
- **Validación de roles**: Solo usuarios autorizados pueden usar comandos admin
- **Persistencia local**: Datos almacenados localmente, no en servicios externos
- **Limpieza automática**: Datos sensibles se limpian automáticamente

## Soporte y Contribución

Este bot está diseñado para ser fácilmente personalizable y extensible. La arquitectura modular permite agregar nuevas funcionalidades sin afectar el código existente.

Para dudas específicas sobre implementación, revisar los comentarios en el código o la documentación inline en cada módulo.