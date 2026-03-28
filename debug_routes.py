import server
print("-" * 30)
print("REGISTERED ROUTES:")
for rule in server.app.url_map.iter_rules():
    print(f"{rule.endpoint:20} {rule.methods} {rule.rule}")
print("-" * 30)
