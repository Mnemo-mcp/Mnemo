interface PaymentRequest {
  amount: number;
  currency: string;
  customerId: string;
}

interface PaymentResponse {
  id: string;
  status: 'pending' | 'completed' | 'failed';
  amount: number;
}

class PaymentProcessor {
  private gateway: string;

  constructor(gateway: string) {
    this.gateway = gateway;
  }

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    return { id: 'pay_1', status: 'completed', amount: request.amount };
  }

  async refundPayment(paymentId: string): Promise<void> {
    // refund logic
  }
}

export function validateAmount(amount: number): boolean {
  return amount > 0 && amount < 1000000;
}

export { PaymentProcessor, PaymentRequest, PaymentResponse };
