#!/usr/bin/env python3
"""
Minimal test server for Insights page development
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import json

app = FastAPI(title="Obby Test Server")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock insights data
MOCK_INSIGHTS = [
    {
        "id": "insight_1",
        "category": "action",
        "priority": "high",
        "title": "Follow up with team about Q4 roadmap",
        "content": "You mentioned discussing Q4 roadmap with the team 5 days ago. Consider following up with team members to ensure alignment on goals and timelines for the upcoming quarter.",
        "relatedFiles": ["notes/team-meeting.md", "docs/roadmap.md"],
        "evidence": {
            "reasoning": "Detected todo item about Q4 discussion with timestamp from 5 days ago",
            "data_points": ["todo item found in notes/team-meeting.md", "5 days since last mention"]
        },
        "timestamp": "2025-10-26T15:00:00Z",
        "dismissed": False,
        "archived": False
    },
    {
        "id": "insight_2",
        "category": "pattern",
        "priority": "medium",
        "title": "Repetitive configuration changes detected",
        "content": "You have been editing config.py multiple times daily for the past week. This might indicate ongoing debugging efforts or configuration optimization that could be consolidated into a more systematic approach.",
        "relatedFiles": ["config.py"],
        "evidence": {
            "reasoning": "Pattern detected in file change frequency",
            "data_points": ["4 changes per day average", "7 consecutive days of activity"]
        },
        "timestamp": "2025-10-26T14:30:00Z",
        "dismissed": False,
        "archived": False
    },
    {
        "id": "insight_3",
        "category": "opportunity",
        "priority": "medium",
        "title": "Documentation gaps detected",
        "content": "Found 3 new API endpoints that lack corresponding test coverage documentation. Consider adding comprehensive tests and documentation to maintain code quality and development standards.",
        "relatedFiles": ["routes/api.py", "routes/endpoints.py"],
        "evidence": {
            "reasoning": "New API endpoints found without corresponding test files",
            "data_points": ["3 undocumented endpoints", "missing test coverage patterns"]
        },
        "timestamp": "2025-10-26T13:45:00Z",
        "dismissed": False,
        "archived": False
    },
    {
        "id": "insight_4",
        "category": "temporal",
        "priority": "low",
        "title": "Admin module activity decline",
        "content": "No activity on admin.py in 12 days after intense development period. This might indicate the feature is complete, but it's worth checking if development was unexpectedly halted.",
        "relatedFiles": ["routes/admin.py"],
        "evidence": {
            "reasoning": "Gap detected in development pattern",
            "data_points": ["12 days since last change", "prior intense activity for 2 weeks"]
        },
        "timestamp": "2025-10-26T12:20:00Z",
        "dismissed": False,
        "archived": False
    },
    {
        "id": "insight_5",
        "category": "relationship",
        "priority": "medium",
        "title": "Related authentication patterns across modules",
        "content": "Found similar authentication handling patterns across 6 different files. Consider extracting into shared utility to reduce duplication and improve maintainability.",
        "relatedFiles": ["auth/auth.py", "routes/api.py", "middleware/auth.py"],
        "evidence": {
            "reasoning": "Code duplication detected across authentication implementation",
            "data_points": ["6 files with similar auth patterns", "potential for consolidation"]
        },
        "timestamp": "2025-10-26T11:15:00Z",
        "dismissed": False,
        "archived": False
    }
]

@app.get("/api/insights")
async def get_insights():
    """Get AI-powered contextual insights"""
    return JSONResponse({
        "success": True,
        "data": MOCK_INSIGHTS,
        "metadata": {
            "time_range_days": 7,
            "max_insights": 20,
            "generated_at": datetime.utcnow().isoformat(),
            "total_insights": len(MOCK_INSIGHTS)
        }
    })

@app.post("/api/insights/{insight_id}/dismiss")
async def dismiss_insight(insight_id: str):
    """Mark an insight as dismissed"""
    return JSONResponse({
        "success": True,
        "message": "Insight dismissed"
    })

@app.post("/api/insights/{insight_id}/archive")
async def archive_insight(insight_id: str):
    """Archive an insight"""
    return JSONResponse({
        "success": True,
        "message": "Insight archived"
    })

@app.get("/api/insights/stats/overview")
async def get_insights_stats():
    """Get overview statistics about insights generation"""
    return JSONResponse({
        "success": True,
        "data": {
            "categories": {
                "action": {"count": 1, "description": "Action items and follow-ups"},
                "pattern": {"count": 1, "description": "Behavioral patterns and routines"},
                "relationship": {"count": 1, "description": "Connections between content"},
                "temporal": {"count": 1, "description": "Time-based insights"},
                "opportunity": {"count": 1, "description": "Opportunities for improvement"}
            },
            "priorities": {
                "critical": {"count": 0, "color": "#ef4444"},
                "high": {"count": 1, "color": "#f97316"}, 
                "medium": {"count": 3, "color": "#eab308"},
                "low": {"count": 1, "color": "#22c55e"}
            },
            "last_generated": datetime.utcnow().isoformat(),
            "total_generated": 5
        }
    })

if __name__ == "__main__":
    print("🚀 Starting Obby Test Server for Insights Development")
    print("📊 Insights API available at: http://localhost:8002/api/insights")
    print("🔗 Frontend should be running at: http://localhost:5173/insights")
    
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)