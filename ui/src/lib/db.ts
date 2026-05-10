import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
    datasources: {
      db: {
        url: process.env.DATABASE_URL,
      },
    },
    // Interaction resiliency
    // Note: Prisma manages pooling internally, but we can tune timeouts if needed via URL params or here
  })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
