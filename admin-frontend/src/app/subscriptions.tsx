import { SubscriptionCard } from "@/components/subscription-card";

export function Subscriptions() {
  const fakeData = [
    {
      id: 1,
      name: '订阅1',
      description: '订阅1的描述',
    },
    {
      id: 2,
      name: '订阅2',
      description: '订阅2的描述',
    },
  ]

  return (
    <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4"
    >
      {fakeData.map((item) => (
        <SubscriptionCard key={item.id} name={item.name} description={item.description} />
      ))}
    </div>
  );
}
