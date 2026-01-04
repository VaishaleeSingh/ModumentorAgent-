"""
Performance monitoring utility for tracking response times
"""
import time
import asyncio
from typing import Dict, Any, Optional, Callable
from functools import wraps
from loguru import logger
from config import config


class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "tool_calls": {},
            "api_calls": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 0,
            "average_response_time": 0.0
        }
        self.start_time = time.time()
    
    def track_tool_call(self, tool_name: str, duration: float, success: bool = True):
        """Track tool call performance"""
        if tool_name not in self.metrics["tool_calls"]:
            self.metrics["tool_calls"][tool_name] = {
                "calls": 0,
                "total_time": 0.0,
                "successes": 0,
                "failures": 0,
                "average_time": 0.0
            }
        
        metric = self.metrics["tool_calls"][tool_name]
        metric["calls"] += 1
        metric["total_time"] += duration
        
        if success:
            metric["successes"] += 1
        else:
            metric["failures"] += 1
        
        metric["average_time"] = metric["total_time"] / metric["calls"]
    
    def track_api_call(self, api_name: str, duration: float, success: bool = True):
        """Track API call performance"""
        if api_name not in self.metrics["api_calls"]:
            self.metrics["api_calls"][api_name] = {
                "calls": 0,
                "total_time": 0.0,
                "successes": 0,
                "failures": 0,
                "average_time": 0.0
            }
        
        metric = self.metrics["api_calls"][api_name]
        metric["calls"] += 1
        metric["total_time"] += duration
        
        if success:
            metric["successes"] += 1
        else:
            metric["failures"] += 1
        
        metric["average_time"] = metric["total_time"] / metric["calls"]
    
    def track_cache_hit(self):
        """Track cache hit"""
        self.metrics["cache_hits"] += 1
    
    def track_cache_miss(self):
        """Track cache miss"""
        self.metrics["cache_misses"] += 1
    
    def track_request(self, duration: float):
        """Track overall request performance"""
        self.metrics["total_requests"] += 1
        
        # Update average response time
        total_time = self.metrics["average_response_time"] * (self.metrics["total_requests"] - 1) + duration
        self.metrics["average_response_time"] = total_time / self.metrics["total_requests"]
    
    def get_performance_summary(self) -> str:
        """Get a formatted performance summary"""
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        cache_hit_rate = 0
        if self.metrics["cache_hits"] + self.metrics["cache_misses"] > 0:
            cache_hit_rate = (self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"])) * 100
        
        summary = f"""📊 **Performance Summary**

⏱️ **Uptime:** {hours}h {minutes}m
📈 **Total Requests:** {self.metrics['total_requests']}
⚡ **Average Response Time:** {self.metrics['average_response_time']:.2f}s
💾 **Cache Hit Rate:** {cache_hit_rate:.1f}%

🔧 **Tool Performance:**
"""
        
        for tool_name, metric in self.metrics["tool_calls"].items():
            success_rate = (metric["successes"] / metric["calls"]) * 100 if metric["calls"] > 0 else 0
            summary += f"• **{tool_name}:** {metric['average_time']:.2f}s avg ({success_rate:.1f}% success)\n"
        
        summary += "\n🌐 **API Performance:**\n"
        for api_name, metric in self.metrics["api_calls"].items():
            success_rate = (metric["successes"] / metric["calls"]) * 100 if metric["calls"] > 0 else 0
            summary += f"• **{api_name}:** {metric['average_time']:.2f}s avg ({success_rate:.1f}% success)\n"
        
        return summary
    
    def get_slowest_operations(self, limit: int = 5) -> list:
        """Get the slowest operations for optimization"""
        all_ops = []
        
        for tool_name, metric in self.metrics["tool_calls"].items():
            all_ops.append({
                "name": f"Tool: {tool_name}",
                "avg_time": metric["average_time"],
                "calls": metric["calls"]
            })
        
        for api_name, metric in self.metrics["api_calls"].items():
            all_ops.append({
                "name": f"API: {api_name}",
                "avg_time": metric["average_time"],
                "calls": metric["calls"]
            })
        
        # Sort by average time (slowest first)
        all_ops.sort(key=lambda x: x["avg_time"], reverse=True)
        return all_ops[:limit]


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def track_performance(operation_type: str, name: str):
    """Decorator to track performance of functions"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                duration = time.time() - start_time
                if operation_type == "tool":
                    performance_monitor.track_tool_call(name, duration, success)
                elif operation_type == "api":
                    performance_monitor.track_api_call(name, duration, success)
                elif operation_type == "request":
                    performance_monitor.track_request(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                duration = time.time() - start_time
                if operation_type == "tool":
                    performance_monitor.track_tool_call(name, duration, success)
                elif operation_type == "api":
                    performance_monitor.track_api_call(name, duration, success)
                elif operation_type == "request":
                    performance_monitor.track_request(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 