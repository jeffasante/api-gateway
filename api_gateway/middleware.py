# api_gateway/middleware.py

import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from prometheus_client import Counter, Histogram
import json

# Set up logging
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

REQUEST_COUNT = Counter(
    'request_count_total',
    'Total request count',
    ['method', 'endpoint', 'status']
)

RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_total',
    'Number of rate limit exceeded events',
    ['user_type']
)

class APIGatewayMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        # Configure rate limits (requests per day)
        self.rate_limits = {
            'authenticated': {'limit': 100000, 'window': 86400},  # 100K/day
            'anonymous': {'limit': 1000, 'window': 86400},       # 1K/day
        }

    def _get_client_ip(self, request):
        """Extract client IP from request, handling proxy headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _check_rate_limit(self, request):
        """Check if request exceeds rate limit"""
        if request.user.is_authenticated:
            rate_config = self.rate_limits['authenticated']
            key_prefix = f'rate-limit-auth-{request.user.id}'
            user_type = 'authenticated'
        else:
            rate_config = self.rate_limits['anonymous']
            key_prefix = f'rate-limit-anon-{self._get_client_ip(request)}'
            user_type = 'anonymous'

        try:
            request_count = cache.get(key_prefix, 0)
            if request_count >= rate_config['limit']:
                RATE_LIMIT_EXCEEDED.labels(user_type=user_type).inc()
                return False
            cache.set(key_prefix, request_count + 1, timeout=rate_config['window'])
            return True
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return True  # Allow request on cache failure

    def _log_request(self, request, response, duration):
        """Log request details with enhanced information"""
        try:
            log_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'user_id': request.user.id if request.user.is_authenticated else None,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'content_length': len(response.content) if hasattr(response, 'content') else 0,
                'referer': request.META.get('HTTP_REFERER', ''),
            }
            
            # Add request body for non-GET requests (careful with sensitive data)
            if request.method not in ['GET', 'HEAD'] and request.body:
                try:
                    body = json.loads(request.body)
                    # Remove sensitive fields if necessary
                    if 'password' in body:
                        body['password'] = '[FILTERED]'
                    log_data['request_body'] = body
                except json.JSONDecodeError:
                    log_data['request_body'] = '[NOT JSON]'
            
            logger.info('API Request', extra={'request_data': log_data})
            
        except Exception as e:
            logger.error(f"Logging failed: {str(e)}")

    def process_request(self, request):
        """Process incoming request"""
        if not self._check_rate_limit(request):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'detail': 'Too many requests. Please try again later.'
            }, status=429)

    def process_response(self, request, response):
        """Process outgoing response and collect metrics"""
        # Calculate request duration
        request_start_time = getattr(request, '_request_start_time', time.time())
        duration = time.time() - request_start_time
        
        # Update Prometheus metrics
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        
        # Log request details
        self._log_request(request, response, duration)
        
        # Add performance headers
        response['X-Response-Time'] = str(round(duration * 1000, 2))
        
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Store request start time"""
        request._request_start_time = time.time()
        return None

    def process_exception(self, request, exception):
        """Handle and log exceptions"""
        logger.error(f'Request failed: {str(exception)}', 
                    extra={
                        'path': request.path,
                        'method': request.method,
                        'user_id': request.user.id if request.user.is_authenticated else None,
                        'exception': str(exception)
                    },
                    exc_info=True)
        return JsonResponse({
            'error': 'Internal server error',
            'detail': str(exception) if settings.DEBUG else 'An unexpected error occurred'
        }, status=500)