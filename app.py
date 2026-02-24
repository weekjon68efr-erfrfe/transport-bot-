"""
Main Flask application for WhatsApp bot
"""
from flask import Flask, request, jsonify
from datetime import datetime

from config import Config, ConfigError
from bot.handlers import BotHandlers
from services.whatsapp import WhatsAppClient
from services.photo import PhotoService
from utils.logger import logger, setup_logger

# Initialize Flask app
app = Flask(__name__)

# Initialize services
try:
    Config.validate()
    whatsapp = WhatsAppClient()
    handlers = BotHandlers()
    photo_service = PhotoService()
    logger.info("🚀 Bot initialized successfully")
except ConfigError as e:
    logger.error(f"Configuration error: {e}")
    raise
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    raise


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook from Green API"""
    try:
        data = request.json
        logger.debug(f"Webhook received: {data.get('typeWebhook')}")
        
        # Parse webhook data
        parsed = whatsapp.parse_webhook(data)
        
        if not parsed:
            return jsonify({"status": "ok"}), 200
        
        phone = parsed['phone']
        text = parsed['text']
        has_media = parsed['has_media']
        media_data = parsed['media_data']
        
        logger.info(f"📱 Message from {phone}: {text or '[media]'}")
        
        # Process message
        response = handlers.process_message(
            phone=phone,
            text=text,
            has_media=has_media,
            media_data=media_data
        )
        
        # Send response
        if response:
            success = whatsapp.send_message(phone, response)
            if success:
                logger.info(f"✅ Response sent to {phone}")
            else:
                logger.error(f"❌ Failed to send response to {phone}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "WhatsApp Weight Bot",
        "timestamp": datetime.now().isoformat(),
        "config_valid": True
    }), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Basic metrics endpoint"""
    return jsonify({
        "uptime": "TODO",
        "messages_processed": 0,
        "photos_stored": len(os.listdir(Config.UPLOAD_FOLDER)) if os.path.exists(Config.UPLOAD_FOLDER) else 0
    }), 200


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


def cleanup_old_files():
    """Cleanup old photos periodically"""
    try:
        photo_service.cleanup_old_photos(days=30)
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Print startup banner
    logger.info("=" * 60)
    logger.info("🚚 WHATSAPP WEIGHT BOT")
    logger.info("=" * 60)
    logger.info(f"📁 Upload folder: {Config.UPLOAD_FOLDER}")
    logger.info(f"📊 Log level: {Config.LOG_LEVEL}")
    logger.info(f"🌐 Server: http://localhost:5000")
    logger.info("=" * 60)
    
    # Run app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Set to False in production
        threaded=True
    )