import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
 } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function SubscriptionCard(
  { name, description }: { name: string; description: string }
) {
  return (
    <Card
      className="min-w-2"
    >
      <CardHeader>
        <CardTitle>{name}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription>{description}</CardDescription>
      </CardContent>
      <CardFooter>
        <Button size="sm">查看</Button>
      </CardFooter>
    </Card>
  );
}
