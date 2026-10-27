from datetime import datetime, timedelta


def demo_events(now: datetime, kind="busy") -> list[dict]:
    if kind == "empty":
        return []
    examples = [
        (0, 8, 0, "Morning walk"), (0, 9, 30, "Design review"), (0, 13, 15, "Project check-in"),
        (1, 9, 0, "Focus time"), (1, 14, 30, "Pick up groceries"),
        (2, 8, 0, "Team planning"), (2, 12, 0, "Lunch with Sam"), (2, 16, 0, "Dentist"),
        (3, 10, 0, "Coffee with Maya"), (3, 17, 30, "Dinner with friends"),
        (4, 9, 0, "Farmers market"), (4, 14, 0, "Family lunch"), (4, 21, 30, "Movie night"),
        (5, 10, 0, "Read at the park"), (5, 16, 0, "Call home"),
        (6, 8, 0, "Weekly planning"), (6, 17, 0, "Evening run"),
    ]
    if kind == "sparse":
        examples = [(2, 8, 0, "Design review"),(12,14,0,"Lunch with friends"),(38,10,30,"Home appointment")]
    result=[]
    for i,(offset,hour,minute,title) in enumerate(examples):
        start=(now+timedelta(days=offset)).replace(hour=hour,minute=minute,second=0,microsecond=0)
        result.append({"id":f"demo-{i}","summary":title,"start":start.isoformat(),"end":(start+timedelta(minutes=45)).isoformat()})
    return result
