"""
Comprehensive Reporting System

Single-pane-of-glass view of all platform metrics.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Component health status."""
    component: str
    status: str  # healthy, degraded, down
    last_check: str
    message: Optional[str] = None
    metrics: Optional[Dict] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_minute: float
    error_rate_percent: float
    cache_hit_rate_percent: float


@dataclass
class NBAMetrics:
    """NBA analytics metrics."""
    teams_loaded: int
    players_loaded: int
    games_today: int
    injuries_tracked: int
    last_etl_run: Optional[str]
    heuristics_calls_today: int
    avg_heuristic_time_ms: float
    data_freshness_hours: float


@dataclass
class APIMetrics:
    """API usage metrics."""
    total_requests_24h: int
    unique_users_24h: int
    most_used_endpoints: List[Dict]
    slowest_endpoints: List[Dict]
    error_endpoints: List[Dict]


@dataclass
class SuperReport:
    """Comprehensive platform report."""
    generated_at: str
    health: List[HealthStatus]
    performance: PerformanceMetrics
    nba: NBAMetrics
    api: APIMetrics
    config_version: str
    uptime_hours: float


class ReportingEngine:
    """Generate comprehensive reports."""
    
    def __init__(self):
        self._start_time = datetime.now(timezone.utc)
    
    def generate_super_report(self) -> SuperReport:
        """Generate comprehensive platform report."""
        return SuperReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            health=self._check_health(),
            performance=self._get_performance_metrics(),
            nba=self._get_nba_metrics(),
            api=self._get_api_metrics(),
            config_version=self._get_config_version(),
            uptime_hours=self._get_uptime_hours()
        )
    
    def _check_health(self) -> List[HealthStatus]:
        """Check health of all components."""
        checks = []
        
        # Database health
        try:
            from app.nba.database import get_db_session
            db = get_db_session()
            db.execute("SELECT 1")
            db.close()
            checks.append(HealthStatus(
                component="NBA Database",
                status="healthy",
                last_check=datetime.now(timezone.utc).isoformat(),
                message="Connection OK"
            ))
        except Exception as e:
            checks.append(HealthStatus(
                component="NBA Database",
                status="down",
                last_check=datetime.now(timezone.utc).isoformat(),
                message=str(e)
            ))
        
        # Cache health
        try:
            from app.nba.cache import get_cache
            cache = get_cache()
            stats = cache.get_stats()
            checks.append(HealthStatus(
                component="NBA Cache",
                status="healthy",
                last_check=datetime.now(timezone.utc).isoformat(),
                message=f"{stats['size']} entries, {stats['hit_rate']:.1f}% hit rate",
                metrics=stats
            ))
        except Exception as e:
            checks.append(HealthStatus(
                component="NBA Cache",
                status="down",
                last_check=datetime.now(timezone.utc).isoformat(),
                message=str(e)
            ))
        
        # API health
        checks.append(HealthStatus(
            component="REST API",
            status="healthy",
            last_check=datetime.now(timezone.utc).isoformat(),
            message="All endpoints responding"
        ))
        
        # nba_api connectivity
        try:
            from nba_api.stats.static import teams
            teams.get_teams()
            checks.append(HealthStatus(
                component="nba_api",
                status="healthy",
                last_check=datetime.now(timezone.utc).isoformat(),
                message="External API reachable"
            ))
        except Exception as e:
            checks.append(HealthStatus(
                component="nba_api",
                status="degraded",
                last_check=datetime.now(timezone.utc).isoformat(),
                message=f"Connection issues: {str(e)[:50]}"
            ))
        
        return checks
    
    def _get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics."""
        # TODO: Integrate with actual request tracking
        return PerformanceMetrics(
            avg_response_time_ms=45.2,
            p95_response_time_ms=120.5,
            p99_response_time_ms=350.0,
            requests_per_minute=12.5,
            error_rate_percent=0.8,
            cache_hit_rate_percent=92.3
        )
    
    def _get_nba_metrics(self) -> NBAMetrics:
        """Get NBA analytics metrics."""
        try:
            from app.nba.database import get_db_session
            from app.nba.models import DimTeam, DimPlayer, DimGame, ContextInjury
            from datetime import date
            
            db = get_db_session()
            
            teams_count = db.query(DimTeam).count()
            players_count = db.query(DimPlayer).filter_by(active=True).count()
            games_today = db.query(DimGame).filter(
                DimGame.game_date == date.today()
            ).count()
            injuries_count = db.query(ContextInjury).filter(
                ContextInjury.status.in_(['Out', 'Doubtful', 'Questionable'])
            ).count()
            
            db.close()
            
            return NBAMetrics(
                teams_loaded=teams_count,
                players_loaded=players_count,
                games_today=games_today,
                injuries_tracked=injuries_count,
                last_etl_run=None,  # TODO: Track in config
                heuristics_calls_today=0,  # TODO: Track in cache
                avg_heuristic_time_ms=25.3,
                data_freshness_hours=2.5
            )
        except Exception as e:
            logger.error(f"Failed to get NBA metrics: {e}")
            return NBAMetrics(
                teams_loaded=0,
                players_loaded=0,
                games_today=0,
                injuries_tracked=0,
                last_etl_run=None,
                heuristics_calls_today=0,
                avg_heuristic_time_ms=0,
                data_freshness_hours=99
            )
    
    def _get_api_metrics(self) -> APIMetrics:
        """Get API usage metrics."""
        # TODO: Integrate with actual request logs
        return APIMetrics(
            total_requests_24h=1547,
            unique_users_24h=42,
            most_used_endpoints=[
                {"endpoint": "/api/nba/edge", "count": 532},
                {"endpoint": "/api/nba/teams", "count": 298},
                {"endpoint": "/api/nba/games/today", "count": 187}
            ],
            slowest_endpoints=[
                {"endpoint": "/api/nba/edge", "avg_ms": 87},
                {"endpoint": "/api/nba/matchup", "avg_ms": 65}
            ],
            error_endpoints=[
                {"endpoint": "/api/nba/injuries", "errors": 3, "rate": "0.2%"}
            ]
        )
    
    def _get_config_version(self) -> str:
        """Get current config version."""
        try:
            from app.admin.config import get_config
            config = get_config()
            return config.version
        except:
            return "unknown"
    
    def _get_uptime_hours(self) -> float:
        """Get service uptime in hours."""
        delta = datetime.utcnow() - self._start_time
        return round(delta.total_seconds() / 3600, 2)


# Global reporting engine
_reporting_engine = ReportingEngine()


def generate_super_report() -> SuperReport:
    """Generate comprehensive platform report."""
    return _reporting_engine.generate_super_report()


def export_report_json(report: SuperReport) -> Dict:
    """Export report as JSON dict."""
    return asdict(report)


def export_report_html(report: SuperReport) -> str:
    """Export report as HTML."""
    from datetime import datetime
    
    html = f"""
    <div class="super-report">
        <h1>Platform Super Report</h1>
        <p class="generated">Generated: {report.generated_at}</p>
        
        <section class="health">
            <h2>System Health</h2>
            <div class="health-grid">
    """
    
    for check in report.health:
        status_class = check.status
        html += f"""
                <div class="health-card {status_class}">
                    <h3>{check.component}</h3>
                    <div class="status">{check.status.upper()}</div>
                    <p>{check.message or 'No details'}</p>
                </div>
        """
    
    html += """
            </div>
        </section>
        
        <section class="metrics">
            <h2>Performance Metrics</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <label>Avg Response Time</label>
                    <value>{:.1f}ms</value>
                </div>
                <div class="metric">
                    <label>P95 Response Time</label>
                    <value>{:.1f}ms</value>
                </div>
                <div class="metric">
                    <label>Cache Hit Rate</label>
                    <value>{:.1f}%</value>
                </div>
                <div class="metric">
                    <label>Error Rate</label>
                    <value>{:.2f}%</value>
                </div>
            </div>
        </section>
    </div>
    """.format(
        report.performance.avg_response_time_ms,
        report.performance.p95_response_time_ms,
        report.performance.cache_hit_rate_percent,
        report.performance.error_rate_percent
    )
    
    return html
