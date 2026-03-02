from django.core.management.base import BaseCommand
from prescriptions.models import InteractionLog
from inventory.models import Drug
from utils.ml_interaction_model import MLInteractionModel
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Train AI interaction model on historical data'
    
    def handle(self, *args, **options):
        self.stdout.write("🤖 Training AI Interaction Model...")
        
        # Initialize model
        model = MLInteractionModel()
        
        # Load historical interactions
        interactions = InteractionLog.objects.all()[:1000]
        drugs = Drug.objects.all()
        
        self.stdout.write(f"Loaded {len(interactions)} historical interactions")
        self.stdout.write(f"Loaded {len(drugs)} drugs")
        
        # Train model
        model.train_model()
        
        # Save model
        model.save_model('models/interaction_model.pkl')
        
        self.stdout.write(self.style.SUCCESS("✅ Model trained and saved successfully!"))