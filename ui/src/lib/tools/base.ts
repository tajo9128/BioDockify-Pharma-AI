
export interface ToolConfig {
    name: string
    description: string
    category: string
    version: string
    requiredParams: string[]
    optionalParams: string[]
}

export interface ToolInput {
    [key: string]: any
}

export interface ToolOutput {
    success: boolean
    data?: any
    error?: string
    metadata?: any
}

export abstract class BaseTool {
    abstract config: ToolConfig

    abstract execute(input: ToolInput): Promise<ToolOutput>

    protected success(data: any, metadata?: any): ToolOutput {
        return { success: true, data, metadata }
    }

    protected error(message: string, metadata?: any): ToolOutput {
        return { success: false, error: message, metadata }
    }
}
