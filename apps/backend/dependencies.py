from config import get_settings
from db.behavior_repository import BehaviorRepository
from services.analytics_service import AnalyticsService
from services.adaptation_feedback_service import AdaptationFeedbackService
from services.adaptation_rl_service import AdaptationRLService
from services.adaptation_service import AdaptationService
from services.behavior_session_service import BehaviorSessionService
from services.intervention_playback_service import InterventionPlaybackService
from services.realtime_hub import RealtimeHub

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

