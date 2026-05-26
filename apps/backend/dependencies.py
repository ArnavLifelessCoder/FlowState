from config import get_settings
from db.behavior_repository import BehaviorRepository
from services.analytics_service import AnalyticsService
from services.assessment_service import AssessmentService
from services.audio_service import AudioService
from services.auth_service import AuthService
from services.adaptation_feedback_service import AdaptationFeedbackService
from services.adaptation_rl_service import AdaptationRLService
from services.adaptation_service import AdaptationService
from services.behavior_session_service import BehaviorSessionService
from services.emotion_pipeline import EmotionPipeline
from services.fusion_service import FusionService
from services.intervention_playback_service import InterventionPlaybackService
from services.memory_service import MemoryService
from services.notification_gating_service import NotificationGatingService
from services.privacy_service import PrivacyService
from services.realtime_hub import RealtimeHub
from services.session_management_service import SessionManagementService
from services.team_analytics_service import TeamAnalyticsService
from services.vision_service import VisionService

settings = get_settings()
behavior_repository = BehaviorRepository(settings.database_url)
behavior_repository.initialize()
behavior_sessions = BehaviorSessionService(
    repository=behavior_repository, window_size=settings.behavior_window_size
)
realtime_hub = RealtimeHub()
adaptation_service = AdaptationService()
adaptation_rl_service = AdaptationRLService(
    repository=behavior_repository,
    alpha=settings.rl_alpha,
    gamma=settings.rl_gamma,
    epsilon=settings.rl_epsilon,
)
adaptation_feedback_service = AdaptationFeedbackService(
    repository=behavior_repository, rl_service=adaptation_rl_service
)
intervention_playback_service = InterventionPlaybackService(behavior_repository)
analytics_service = AnalyticsService(behavior_repository)
memory_service = MemoryService(behavior_repository)
session_management_service = SessionManagementService(
    repository=behavior_repository, memory_service=memory_service,
)
privacy_service = PrivacyService(behavior_repository)
notification_gating_service = NotificationGatingService(
    behavior_sessions=behavior_sessions,
)
team_analytics_service = TeamAnalyticsService(behavior_repository)
auth_service = AuthService(behavior_repository)

# ── Multimodal Emotion Pipeline ───────────────────────────────────
vision_service = VisionService()
audio_service = AudioService()
fusion_service = FusionService()
emotion_pipeline = EmotionPipeline(
    repository=behavior_repository,
    vision_service=vision_service,
    audio_service=audio_service,
    fusion_service=fusion_service,
    behavior_sessions=behavior_sessions,
)
assessment_service = AssessmentService(behavior_repository)
